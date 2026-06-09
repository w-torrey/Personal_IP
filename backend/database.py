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

def get_or_create_watchlist(label: str, person: str = None, organization: str = None,
                             keywords: list = None, include_sites: list = None,
                             exclude_sites: list = None, category: str = "Uncategorized") -> int:
    query_params = json.dumps({
        "person": person,
        "organization": organization,
        "keywords": keywords,
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
            INSERT INTO watchlists (label, person, organization, category, query_params)
            VALUES (:label, :person, :organization, :category, CAST(:query_params AS jsonb))
            RETURNING id
        """), {
            "label": label,
            "person": person,
            "organization": organization,
            "category": category,
            "query_params": query_params,
        })
        conn.commit()
        return result.fetchone()[0]

def update_watchlist(watchlist_id: int, label: str, person: str = None, organization: str = None,
                      keywords: list = None, include_sites: list = None,
                      exclude_sites: list = None, category: str = "Uncategorized"):
    query_params = json.dumps({
        "person": person,
        "organization": organization,
        "keywords": keywords,
        "include_sites": include_sites,
        "exclude_sites": exclude_sites,
    })
    with engine.connect() as conn:
        conn.execute(text("""
            UPDATE watchlists
            SET label = :label,
                person = :person,
                organization = :organization,
                category = :category,
                query_params = CAST(:query_params AS jsonb)
            WHERE id = :watchlist_id
        """), {
            "watchlist_id": watchlist_id,
            "label": label,
            "person": person,
            "organization": organization,
            "category": category,
            "query_params": query_params,
        })
        conn.commit()

def get_new_alerts():
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT r.id, w.person, w.organization, w.category, w.label, r.title, r.link, r.snippet, r.source, r.date_found, r.fetched_at
            FROM results r
            JOIN watchlists w ON r.watchlist_id = w.id
            WHERE r.is_new = TRUE
            ORDER BY r.fetched_at DESC
        """))
        rows = result.fetchall()
    return [
        {
            "id": row[0],
            "person": row[1],
            "organization": row[2],
            "category": row[3],
            "label": row[4],
            "title": row[5],
            "link": row[6],
            "snippet": row[7],
            "source": row[8],
            "date_found": row[9],
            "fetched_at": str(row[10]),
        }
        for row in rows
    ]

def get_all_watchlists():
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT id, label, person, organization, category, query_params 
            FROM watchlists
        """))
        rows = result.fetchall()
    return [
        {
            "id": row[0],
            "label": row[1],
            "person": row[2],
            "organization": row[3],
            "category": row[4],
            "query_params": row[5],
        }
        for row in rows
    ]