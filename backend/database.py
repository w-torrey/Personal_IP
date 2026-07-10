from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
import json

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres@localhost:5432/IndexPulse")
engine = create_engine(DB_URL)

def save_results(watchlist_id: int, results: list):
    saved = 0
    skipped = 0
    with engine.connect() as conn:
        for item in results:
            try:
                conn.execute(text("""
                    INSERT INTO results (watchlist_id, title, link, snippet, source, date_found)
                    VALUES (:watchlist_id, :title, :link, :snippet, :source, :date_found)
                    ON CONFLICT (link) DO NOTHING
                """), {
                    "watchlist_id": watchlist_id,
                    "title": item.get("title"),
                    "link": item.get("link"),
                    "snippet": item.get("snippet"),
                    "source": item.get("source"),
                    "date_found": item.get("date"),
                })
                saved += 1
            except Exception as e:
                skipped += 1
                print(f"Skipped: {e}")
        conn.commit()
    return {"saved": saved, "skipped": skipped}

def get_or_create_watchlist(label: str, keywords: list = None, exclude_keywords: list = None,
                             include_sites: list = None, exclude_sites: list = None,
                             category: str = "Uncategorized") -> int:
    query_params = json.dumps({
        "keywords": keywords,
        "exclude_keywords": exclude_keywords,
        "include_sites": include_sites,
        "exclude_sites": exclude_sites,
    })
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT id FROM watchlists WHERE label = :label
        """), {"label": label})
        row = result.fetchone()
        if row:
            return row[0]
        result = conn.execute(text("""
            INSERT INTO watchlists (label, category, query_params)
            VALUES (:label, :category, CAST(:query_params AS jsonb))
            RETURNING id
        """), {
            "label": label,
            "category": category,
            "query_params": query_params,
        })
        conn.commit()
        return result.fetchone()[0]

def update_watchlist(watchlist_id: int, label: str, keywords: list = None,
                      exclude_keywords: list = None, include_sites: list = None,
                      exclude_sites: list = None, category: str = "Custom"):
    query_params = json.dumps({
        "keywords": keywords,
        "exclude_keywords": exclude_keywords,
        "include_sites": include_sites,
        "exclude_sites": exclude_sites,
    })
    with engine.connect() as conn:
        conn.execute(text("""
            UPDATE watchlists
            SET label = :label,
                category = :category,
                query_params = CAST(:query_params AS jsonb)
            WHERE id = :watchlist_id
        """), {
            "watchlist_id": watchlist_id,
            "label": label,
            "category": category,
            "query_params": query_params,
        })
        conn.commit()

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

def delete_watchlist_db(watchlist_id):
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM results WHERE watchlist_id = :id"), {"id": watchlist_id})
        result = conn.execute(text("DELETE FROM watchlists where id = :id"), {"id": watchlist_id})
        conn.commit()
        return result.rowcount

def create_user(email: str, hashed_password: str):
    with engine.connect() as conn:
        conn.execute(text("""
                          INSERT INTO users (email, hashed_password)
                          VALUES (:email, :hashed_password)
                          """), {
                              "email": email,
                              "hashed_password": hashed_password
                          })
        conn.commit()

def get_user_by_email(email: str):
    with engine.connect() as conn:
        result = conn.execute(text(""" SELECT email, hashed_password FROM users WHERE email = :email """), {"email": email})
        row = result.fetchone()

    if not row:
        return None
    
    return {"email": row[0], "hashed_password": row[1]}

def mark_as_read(alert_id: int): 
    with engine.connect() as conn:
        result = conn.execute(text("UPDATE results SET is_read = TRUE WHERE id = :id"), {"id": alert_id})
        conn.commit()
        return result.rowcount

def get_new_alerts(watchlist_id: int):
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT r.id, r.title, r.snippet, r.source, r.date_found, r.watchlist_id
            FROM results r
            JOIN watchlists w ON r.watchlist_id = w.id
            WHERE r.watchlist_id = :watchlist_id AND r.is_new = TRUE
            ORDER BY r.fetched_at DESC
        """), {"watchlist_id": watchlist_id})
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

def get_all_alerts(watchlist_id: int):
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT r.id, r.title, r.snippet, r.source, r.date_found, r.watchlist_id
            FROM results r
            JOIN watchlists w ON r.watchlist_id = w.id
            WHERE r.watchlist_id = :watchlist_id
            ORDER BY r.fetched_at DESC
        """), {"watchlist_id": watchlist_id})
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

