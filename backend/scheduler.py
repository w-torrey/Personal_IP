from apscheduler.schedulers.background import BackgroundScheduler
from database import save_results, get_all_watchlists, get_watchlist_alerts, save_digest, save_dossier, get_new_alerts, clear_new_flags
from dork_engine import run_dork
from summary_engine import generate_summary
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# creeate thread to run in a background simplicity
scheduler = BackgroundScheduler()

# meant to run all watchlists at once asdf


def run_all_watchlists():
    # return all watchlists so we can work it
    logger.info("Scheduler triggered — running all watchlist")
    watchlists = get_all_watchlists()
    if not watchlists:
        logger.info("No watchlists found.")
        return

    for w in watchlists:
        logger.info(f"running dork for: {w['label']}")
        # run through and search for query params
        qp = w.get("query_params") or {}
        result = run_dork(
            keywords=qp.get("keywords"),
            exclude_keywords=qp.get("exclude_keywords"),
            include_sites=qp.get("include_sites"),
            exclude_sites=qp.get("exclude_sites"),
        )
        # need to check if worked
        if result["success"]:
            saved = save_results(w["id"], result["results"])
            # ai terminal checker
            logger.info(
                f"Saved: {saved['saved']} new, Skipped: {saved['skipped']} duplicates"
            )
            new_alerts = get_new_alerts(w["id"])
            if not new_alerts: 
                continue
            digest = generate_summary("digest", new_alerts)
            if not digest["success"]: continue
            digests = digest["results"]
            save_digest(w["id"], digests["headline"], digests["narrative"], digests["severity"], digests["alert_ids"])
            clear_new_flags([alert["id"] for alert in new_alerts])

            all_alerts = get_watchlist_alerts(w["id"])
            dossier = generate_summary("dossier", all_alerts)
            if not dossier["success"]: continue
            save_dossier(w["id"], dossier["results"])
        else:
            # failed catch
            logger.error(f"Dork failed for {w['label']}: {result.get('error')}")
    logger.info("Scheduler run complete.")


# create a cron job that calls run all watchlists ^^ at 8 PM
def start_scheduler(interval_hours: int = 24):
    # interval hours isnt used i just realized so maybe remove
    scheduler.add_job(run_all_watchlists, "cron", hour=20, minute=0, id="dork_job")
    scheduler.start()
    logger.info("Scheduler started — running daily at 8:00 PM ET")


# stop background thread
def stop_scheduler():
    scheduler.shutdown()
    logger.info("Scheduler stopped")
