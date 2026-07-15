from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
import json

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres@localhost:5432/IndexPulse")
engine = create_engine(DB_URL)


# Loops through results param and inserts info into results table, dedup logic within SQL query by URL
# note the saved counter overcounts because it includes skipped inserts, for future consideration
def save_results(watchlist_id: int, results: list):
    saved = 0
    skipped = 0
    with engine.connect() as conn:
        for item in results:
            try:
                conn.execute(
                    text("""
                    INSERT INTO results (watchlist_id, title, link, snippet, source, date_found)
                    VALUES (:watchlist_id, :title, :link, :snippet, :source, :date_found)
                    ON CONFLICT (link) DO NOTHING
                """),
                    {
                        "watchlist_id": watchlist_id,
                        "title": item.get("title"),
                        "link": item.get("link"),
                        "snippet": item.get("snippet"),
                        "source": item.get("source"),
                        "date_found": item.get("date"),
                    },
                )
                saved += 1
            except Exception as e:
                skipped += 1
                print(f"Skipped: {e}")
        conn.commit()
    return {"saved": saved, "skipped": skipped}


# takes in inputs for watchlist, converts to json and casts to jsonb, checks for dupes by label and returns id if so, if not, inserts watchlist and returns id for /monitor
def get_or_create_watchlist(
    label: str,
    keywords: list = None,
    exclude_keywords: list = None,
    include_sites: list = None,
    exclude_sites: list = None,
    category: str = "Uncategorized",
):
    query_params = json.dumps(
        {
            "keywords": keywords,
            "exclude_keywords": exclude_keywords,
            "include_sites": include_sites,
            "exclude_sites": exclude_sites,
        }
    )
    with engine.connect() as conn:
        result = conn.execute(
            text("""
            SELECT id FROM watchlists WHERE label = :label
        """),
            {"label": label},
        )
        row = result.fetchone()
        if row:
            return row[0]
        result = conn.execute(
            text("""
            INSERT INTO watchlists (label, category, query_params)
            VALUES (:label, :category, CAST(:query_params AS jsonb))
            RETURNING id
        """),
            {
                "label": label,
                "category": category,
                "query_params": query_params,
            },
        )
        conn.commit()
        return result.fetchone()[0]


# Overwites existing watchlist with new params, converts to json and casts to jsonb and updates database
# note for future, needs to return some info for the endpoint to id a failure
def db_update_watchlist(
    watchlist_id: int,
    label: str,
    keywords: list = None,
    exclude_keywords: list = None,
    include_sites: list = None,
    exclude_sites: list = None,
    category: str = "Custom",
):
    query_params = json.dumps(
        {
            "keywords": keywords,
            "exclude_keywords": exclude_keywords,
            "include_sites": include_sites,
            "exclude_sites": exclude_sites,
        }
    )
    with engine.connect() as conn:
        conn.execute(
            text("""
            UPDATE watchlists
            SET label = :label,
                category = :category,
                query_params = CAST(:query_params AS jsonb)
            WHERE id = :watchlist_id
        """),
            {
                "watchlist_id": watchlist_id,
                "label": label,
                "category": category,
                "query_params": query_params,
            },
        )
        conn.commit()


# Query to get all alerts to feed into /alerts enpoint
def get_alerts():
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT r.id, w.category, w.label, r.title, r.link, r.snippet, r.source, r.date_found, r.fetched_at, r.is_read, r.watchlist_id, w.query_params
            FROM results r
            JOIN watchlists w ON r.watchlist_id = w.id
            ORDER BY r.fetched_at DESC
        """))
        rows = result.fetchall()
    return [
        {
            "id": row[0],
            "category": row[1],
            "label": row[2],
            "title": row[3],
            "link": row[4],
            "snippet": row[5],
            "source": row[6],
            "date_found": row[7],
            "fetched_at": str(row[8]),
            "is_read": row[9],
            "watchlist_id": row[10],
            "query_params": row[11],
        }
        for row in rows
    ]


# Query to retrieve all watchlists with relavant info for /watchlists endpoint, also used in scheduler
def get_all_watchlists():
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT id, label, category, query_params
            FROM watchlists
        """))
        rows = result.fetchall()
    return [
        {
            "id": row[0],
            "label": row[1],
            "category": row[2],
            "query_params": row[3],
        }
        for row in rows
    ]


# Query to delete a watchlist by id and all relavnt info related to it, returns 1 for success 0 for failure to find watchlist
def delete_watchlist_db(watchlist_id):
    with engine.connect() as conn:
        conn.execute(
            text("DELETE FROM results WHERE watchlist_id = :id"), {"id": watchlist_id}
        )
        result = conn.execute(
            text("DELETE FROM watchlists WHERE id = :id"), {"id": watchlist_id}
        )
        conn.commit()
        return result.rowcount


# Query to insert new user info indcluding already hashed password into users table
def create_user(email: str, hashed_password: str):
    with engine.connect() as conn:
        conn.execute(
            text("""
                          INSERT INTO users (email, hashed_password)
                          VALUES (:email, :hashed_password)
                          """),
            {"email": email, "hashed_password": hashed_password},
        )
        conn.commit()


# Query to retrieve user hashed password by email for verification
def get_user_by_email(email: str):
    with engine.connect() as conn:
        result = conn.execute(
            text(""" SELECT email, hashed_password FROM users WHERE email = :email """),
            {"email": email},
        )
        row = result.fetchone()

    if not row:
        return None

    return {"email": row[0], "hashed_password": row[1]}


# Query to update is_read flag in results and returns rowcount
def mark_as_read(alert_id: int):
    with engine.connect() as conn:
        result = conn.execute(
            text("UPDATE results SET is_read = TRUE WHERE id = :id"), {"id": alert_id}
        )
        conn.commit()
        return result.rowcount
