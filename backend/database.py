from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

# Database connection string
DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres@localhost:5432/IndexPulse")

# Create engine
engine = create_engine(DB_URL)


def get_connection():
    return engine.connect()


def save_results(watchlist_id: int, results: list):
    """
    Saves search results to the database.
    Skips duplicates based on the link (UNIQUE constraint).
    Marks each result as new.
    """
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


def get_or_create_watchlist(person: str, organization: str) -> int:
    """
    Gets existing watchlist ID or creates a new one.
    Returns the watchlist ID.
    """
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT id FROM watchlists
            WHERE person = :person AND organization = :organization
        """), {"person": person, "organization": organization})

        row = result.fetchone()

        if row:
            return row[0]

        # Create new watchlist
        result = conn.execute(text("""
            INSERT INTO watchlists (person, organization)
            VALUES (:person, :organization)
            RETURNING id
        """), {"person": person, "organization": organization})

        conn.commit()
        return result.fetchone()[0]


def get_new_alerts():
    """
    Returns all results flagged as new/unseen.
    """
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT r.id, w.person, w.organization, r.title, r.link, r.snippet, r.source, r.date_found, r.fetched_at
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
            "title": row[3],
            "link": row[4],
            "snippet": row[5],
            "source": row[6],
            "date_found": row[7],
            "fetched_at": str(row[8]),
        }
        for row in rows
    ]


def get_all_watchlists():
    """
    Returns all watchlists from the database.
    """
    with engine.connect() as conn:
        result = conn.execute(text("SELECT id, person, organization FROM watchlists"))
        rows = result.fetchall()

    return [
        {"id": row[0], "person": row[1], "organization": row[2]}
        for row in rows
    ]
