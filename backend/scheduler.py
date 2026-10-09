from apscheduler.schedulers.background import BackgroundScheduler
from database import (
    save_results,
    get_all_watchlists,
    get_watchlist_alerts,
    save_digest,
    save_dossier,
    get_new_alerts,
    clear_new_flags,
)
from dork_engine import run_dork
from summary_engine import generate_summary
from investigator import investigate
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# creeate thread to run in a background simplicity
scheduler = BackgroundScheduler()

# meant to run all watchlists at once


def run_all_watchlists():
    # return all watchlists so we can work it
    logger.info("Scheduler triggered — running all watchlist")
    run_start = time.perf_counter()
    total_saved = 0
    total_skipped = 0
    total_tokens = 0
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
            or_keywords=qp.get("or_keywords"),
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
            total_saved += saved["saved"]
            total_skipped += saved["skipped"]
            try:
                new_alerts = get_new_alerts(w["id"])
                if not new_alerts:
                    continue
                digest = investigate(w, new_alerts)
                if digest["success"]:
                    logger.info(f"Investigation {w['label']}: tool calls {digest['tool_calls']}")
                else:
                    # fall back to a plain one-call digest so the run still produces a briefing
                    logger.warning(
                        f"Investigation failed for {w['label']}, using plain digest: {digest['error']}"
                    )
                    digest = generate_summary("digest", new_alerts)
                if not digest["success"]:
                    logger.error(
                        f"Digest failed to generate for {w['label']}: {digest['error']}"
                    )
                    continue
                digests = digest["results"]
                total_tokens += digest.get("input_tokens", 0) + digest.get(
                    "output_tokens", 0
                )
                logger.info(
                    f"Digest {w['label']}: {digest.get('seconds')}s, {digest.get('input_tokens')}in/{digest.get('output_tokens')}out tok"
                )
                save_digest(
                    w["id"],
                    digests["headline"],
                    digests["narrative"],
                    digests["severity"],
                    digests["alert_ids"],
                )
                clear_new_flags([alert["id"] for alert in new_alerts])

                all_alerts = get_watchlist_alerts(w["id"])
                dossier = generate_summary("dossier", all_alerts)
                if not dossier["success"]:
                    logger.error(
                        f"Dossier failed to generate for {w['label']}: {dossier['error']}"
                    )
                    continue
                save_dossier(w["id"], dossier["results"])
                total_tokens += dossier.get("input_tokens", 0) + dossier.get(
                    "output_tokens", 0
                )
                logger.info(
                    f"Dossier {w['label']}: {dossier.get('seconds')}s, {dossier.get('input_tokens')}in/{dossier.get('output_tokens')}out tok"
                )
            except Exception as e:
                logger.error(f"Summary generation failed for {w['label']}: {e}")
        else:
            # failed catch
            logger.error(f"Dork failed for {w['label']}: {result.get('error')}")
    elapsed = time.perf_counter() - run_start
    total = total_saved + total_skipped
    dedup_pct = round(100 * total_skipped / total, 1) if total else 0
    logger.info(
        f"SWEEP DONE in {round(elapsed, 2)}s | {len(watchlists)} watchlists | "
        f"saved {total_saved}, skipped {total_skipped} ({dedup_pct}% dedup) | {total_tokens} tokens"
    )


# create a cron job that calls run all watchlists ^^ at 8 PM
def start_scheduler():
    scheduler.add_job(run_all_watchlists, "cron", hour=20, minute=0, id="dork_job")
    scheduler.start()
    logger.info("Scheduler started — running daily at 8:00 PM ET")


# stop background thread
def stop_scheduler():
    scheduler.shutdown()
    logger.info("Scheduler stopped")
