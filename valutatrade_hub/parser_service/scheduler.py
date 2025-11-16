from typing import Optional, Dict, Any
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from ..logging_config import get_logger
from .config import config
from .updater import RatesUpdater


class ParserScheduler:
    def __init__(self):
        self.logger = get_logger("parser.scheduler")
        self.updater = RatesUpdater()
        self.scheduler: Optional[BackgroundScheduler] = None
        self.is_running = False

    def start(self):
        if self.is_running:
            self.logger.warning("Scheduler is already running")
            return

        try:
            self.scheduler = BackgroundScheduler()

            trigger = IntervalTrigger(minutes=config.UPDATE_INTERVAL_MINUTES)
            self.scheduler.add_job(
                self._scheduled_update,
                trigger,
                id="rates_update",
                name="Currency rates update",
                replace_existing=True
            )

            self.scheduler.add_job(
                self._scheduled_cleanup,
                "interval",
                hours=24,
                id="data_cleanup",
                name="Old data cleanup"
            )

            self.scheduler.start()
            self.is_running = True

            self.logger.info(
                "Parser scheduler started",
                extra={
                    "action": "SCHEDULER_START",
                    "update_interval_minutes": config.UPDATE_INTERVAL_MINUTES
                }
            )

            self.scheduler.add_job(
                self._scheduled_update,
                "date",
                run_date=None,
                id="initial_update"
            )

        except Exception as e:
            self.logger.error(
                f"Failed to start scheduler: {str(e)}",
                extra={
                    "action": "SCHEDULER_ERROR",
                    "error": str(e)
                }
            )
            raise

    def stop(self):
        if self.scheduler and self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            self.logger.info("Parser scheduler stopped",
                             extra={"action": "SCHEDULER_STOP"})

    def _scheduled_update(self):
        try:
            self.logger.debug("Running scheduled rates update")
            results = self.updater.run_update()

            if not results["successful_sources"]:
                self.logger.error("Scheduled update failed for all sources")
            elif results["failed_sources"]:
                self.logger.warning("Scheduled update completed with some failures")
            else:
                self.logger.info("Scheduled update completed successfully")

        except Exception as e:
            self.logger.error(
                f"Scheduled update failed: {str(e)}",
                extra={
                    "action": "SCHEDULED_UPDATE_ERROR",
                    "error": str(e)
                }
            )

    def _scheduled_cleanup(self):
        try:
            self.logger.debug("Running scheduled data cleanup")
            removed_count = self.updater.cleanup_old_data(max_age_days=30)

            if removed_count > 0:
                self.logger.info(f"Cleaned up {removed_count} old records")

        except Exception as e:
            self.logger.error(
                f"Scheduled cleanup failed: {str(e)}",
                extra={
                    "action": "SCHEDULED_CLEANUP_ERROR",
                    "error": str(e)
                }
            )

    def get_status(self) -> Dict[str, Any]:
        if not self.scheduler or not self.is_running:
            return {
                "status": "stopped",
                "is_running": False
            }

        jobs = self.scheduler.get_jobs()
        update_status = self.updater.get_update_status()

        return {
            "status": "running",
            "is_running": True,
            "jobs_count": len(jobs),
            "update_interval_minutes": config.UPDATE_INTERVAL_MINUTES,
            "last_update": update_status.get("last_refresh"),
            "is_fresh": update_status.get("is_fresh", False)
        }
