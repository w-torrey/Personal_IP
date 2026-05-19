from apscheduler.schedulers.background import BackgroundScheduler
from database import save_results, get_or_create_watchlist, get_all_watchlists
from dork_engine import run_dork
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def run_all_watchlists():
    """
    Fetches all watchlists from the database and runs a dork search for each one.
    Saves any new results automatically.
    """
    logger.info("Scheduler triggered — running all watchlists...")

    watchlists = get_all_watchlists()

    if not watchlists:
        logger.info("No watchlists found. Add some via POST /watchlist")
        return

    for w in watchlists:
        logger.info(f"Running dork for: {w['person']} @ {w['organization']}")
        result = run_dork(w["person"], w["organization"])

        if result["success"]:
            saved = save_results(w["id"], result["results"])
            logger.info(f"Saved: {saved['saved']} new, Skipped: {saved['skipped']} duplicates")
        else:
            logger.error(f"Dork failed for {w['person']}: {result.get('error')}")

    logger.info("Scheduler run complete.")


def start_scheduler(interval_hours: int = 24):
    """
    Starts the background scheduler.
    Runs run_all_watchlists() every interval_hours.
    """
    scheduler.add_job(run_all_watchlists, "interval", hours=interval_hours, id="dork_job")
    scheduler.start()
    logger.info(f"Scheduler started — running every {interval_hours} hours")


def stop_scheduler():
    scheduler.shutdown()
    logger.info("Scheduler stopped")