from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
import json

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres@localhost:5432/IndexPulse")
engine = create_engine(DB_URL)

# Loops through results param and inserts info into results table, dedup logic within SQL query by URL
def save_results(watchlist_id: int, results: list):
    saved = 0
    skipped = 0
    with engine.connect() as conn:
        for item in results:
            try:
                result = conn.execute(
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
                if result.rowcount:
                    saved += 1
                else: skipped += 1
            except Exception as e:
                skipped += 1
                print(f"Skipped: {e}")
        conn.commit()
    return {"saved": saved, "skipped": skipped}


# takes in inputs for watchlist, converts to json and casts to jsonb, checks for dupes by label and returns id if so, if not, inserts watchlist and returns id for /monitor
def get_or_create_watchlist(
    label: str,
    keywords: list = None,
    or_keywords: list = None,
    exclude_keywords: list = None,
    include_sites: list = None,
    exclude_sites: list = None,
    category: str = "Uncategorized",
):
    query_params = json.dumps(
        {
            "keywords": keywords,
            "or_keywords": or_keywords,
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
    or_keywords: list = None,
    exclude_keywords: list = None,
    include_sites: list = None,
    exclude_sites: list = None,
    category: str = "Custom",
):
    query_params = json.dumps(
        {
            "keywords": keywords,
            "or_keywords": or_keywords,
            "exclude_keywords": exclude_keywords,
            "include_sites": include_sites,
            "exclude_sites": exclude_sites,
        }
    )
    with engine.connect() as conn:
        result = conn.execute(
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
        return result.rowcount


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


def get_new_alerts(watchlist_id: int):
    with engine.connect() as conn:
        result = conn.execute(
            text("""
            SELECT r.id, r.title, r.snippet, r.source, r.date_found, r.watchlist_id
            FROM results r
            JOIN watchlists w ON r.watchlist_id = w.id
            WHERE r.watchlist_id = :watchlist_id AND r.is_new = TRUE
            ORDER BY r.fetched_at DESC
        """),
            {"watchlist_id": watchlist_id},
        )
        rows = result.fetchall()
    return [
        {
            "id": row[0],
            "title": row[1],
            "snippet": row[2],
            "source": row[3],
            "date_found": row[4],
            "watchlist_id": row[5],
        }
        for row in rows
    ]


def get_watchlist_alerts(watchlist_id: int):
    with engine.connect() as conn:
        result = conn.execute(
            text("""
            SELECT r.id, r.title, r.snippet, r.source, r.date_found, r.watchlist_id
            FROM results r
            JOIN watchlists w ON r.watchlist_id = w.id
            WHERE r.watchlist_id = :watchlist_id
            ORDER BY r.fetched_at DESC
        """),
            {"watchlist_id": watchlist_id},
        )
        rows = result.fetchall()
    return [
        {
            "id": row[0],
            "title": row[1],
            "snippet": row[2],
            "source": row[3],
            "date_found": row[4],
            "watchlist_id": row[5],
        }
        for row in rows
    ]


## This is the method to save the dossier we generate into our db,
## we have an on conflict clause to update when a dossier already exists rather than write and store a whole new one
def save_dossier(watchlist_id: int, summary: str):
    with engine.connect() as conn:
        result = conn.execute(
            text("""
            INSERT INTO dossiers (watchlist_id, summary, updated_at)
            VALUES (:watchlist_id, :summary, NOW())
            ON CONFLICT (watchlist_id) DO UPDATE
            SET summary = EXCLUDED.summary, updated_at = NOW()
                                   """),
            {"watchlist_id": watchlist_id, "summary": summary},
        )
        conn.commit()
        return result.rowcount


def get_dossiers():
    with engine.connect() as conn:
        result = conn.execute(
            text("""
            SELECT d.watchlist_id, d.summary, d.updated_at, w.label, w.category
            FROM dossiers d 
            JOIN watchlists w ON w.id = d.watchlist_id
                                   """),
        )
        rows = result.fetchall()
        return [
            {"watchlist_id": row[0], "summary": row[1], "updated_at": row[2], "label": row[3], "category": row[4]}
            for row in rows
        ]


def save_digest(
    watchlist_id: int,
    headline: str,
    narrative: str,
    severity: str,
    alert_ids: list[int],
):

    alerts = json.dumps(alert_ids)

    with engine.connect() as conn:
        result = conn.execute(
            text("""
            INSERT INTO digests (watchlist_id, headline, narrative, severity, alert_ids)
            VALUES (:watchlist_id, :headline, :narrative, :severity, CAST(:alert_ids AS jsonb))
                                   """),
            {
                "watchlist_id": watchlist_id,
                "headline": headline,
                "narrative": narrative,
                "severity": severity,
                "alert_ids": alerts,
            },
        )
        conn.commit()
        return result.rowcount

def get_digests():
    with engine.connect() as conn:
        result = conn.execute(
            text("""
            SELECT DISTINCT ON (d.watchlist_id)
            d.watchlist_id, d.narrative, d.alert_ids, w.label, d.headline, d.severity, d.generated_at, w.category
            FROM digests d 
            JOIN watchlists w ON w.id = d.watchlist_id
            ORDER BY d.watchlist_id, d.generated_at DESC
                                   """),
        )
        rows = result.fetchall()
        return [
            {"watchlist_id": row[0], "narrative": row[1], "alert_ids": row[2], "label": row[3], "headline": row[4], "severity": row[5], "generated_at": row[6], "category": row[7]}
            for row in rows
        ]


def clear_new_flags(alert_ids: list[int]):
    with engine.connect() as conn:
        result = conn.execute(
            text("UPDATE results SET is_new = FALSE WHERE id = ANY(:ids)"),
            {"ids": alert_ids},
        )
        conn.commit()
        return result.rowcount
