from apscheduler.schedulers.background import BackgroundScheduler
from database import save_results, get_all_watchlists
from dork_engine import run_dork
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

def run_all_watchlists():
    logger.info("Scheduler triggered — running all watchlists...")
    watchlists = get_all_watchlists()
    if not watchlists:
        logger.info("No watchlists found.")
        return
    for w in watchlists:
        logger.info(f"Running dork for: {w['label']}")
        qp = w.get("query_params") or {}
        result = run_dork(
            person=qp.get("person"),
            organization=qp.get("organization"),
            keywords=qp.get("keywords"),
            include_sites=qp.get("include_sites"),
            exclude_sites=qp.get("exclude_sites"),
        )
        if result["success"]:
            saved = save_results(w["id"], result["results"])
            logger.info(f"Saved: {saved['saved']} new, Skipped: {saved['skipped']} duplicates")
        else:
            logger.error(f"Dork failed for {w['label']}: {result.get('error')}")
    logger.info("Scheduler run complete.")

def start_scheduler(interval_hours: int = 24):
    scheduler.add_job(run_all_watchlists, "cron", hour=20, minute=0, id="dork_job")
    scheduler.start()
    logger.info("Scheduler started — running daily at 8:00 PM ET")

def stop_scheduler():
    scheduler.shutdown()
    logger.info("Scheduler stopped")