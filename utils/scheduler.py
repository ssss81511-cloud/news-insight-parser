"""
Automatic scheduler for regular parsing

Features:
- Per-source scheduling with predefined intervals
- Enable/disable individual sources
- Global enable/disable for all auto-parsing
- Logging and error handling
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from loguru import logger
import json
import os


class AutoScheduler:
    """
    Automatic scheduler for parsing tasks

    Supports:
    - Individual source enable/disable
    - Predefined optimal intervals per source
    - Interval-based and cron-based triggers
    - Persistent configuration
    """

    CONFIG_FILE = 'data/scheduler_config.json'

    def __init__(self):
        """Initialize scheduler"""
        self.scheduler = BackgroundScheduler()
        self.config = self._load_config()
        self.orchestrator = None
        self.analyze_callback = None

    def _load_config(self) -> dict:
        """Load scheduler configuration from file"""
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load scheduler config: {e}")

        # Default configuration
        return {
            'auto_parse_enabled': False,  # Global switch
            'analyze_after_parse': True,
            'sources': {},  # Will be populated dynamically
            'last_analyze': None,
        }

    def _save_config(self):
        """Save scheduler configuration to file"""
        try:
            os.makedirs('data', exist_ok=True)
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save scheduler config: {e}")

    def set_orchestrator(self, orchestrator):
        """
        Set orchestrator for parsing

        Args:
            orchestrator: ParserOrchestrator instance
        """
        self.orchestrator = orchestrator

    def set_analyze_callback(self, callback):
        """
        Set callback function for signal analysis

        Args:
            callback: Function to call for analysis (should accept no args)
        """
        self.analyze_callback = callback

    def start(self):
        """Start the scheduler"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started")

            # Apply current configuration
            self._apply_config()

    def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")

    def _apply_config(self):
        """Apply current configuration to scheduler"""
        # Remove all existing jobs
        self.scheduler.remove_all_jobs()

        if not self.config.get('auto_parse_enabled', False):
            logger.info("Auto-parsing is disabled")
            return

        if not self.orchestrator:
            logger.warning("Orchestrator not set, cannot schedule parsing")
            return

        # Import here to avoid circular dependency
        from parsers.sources_config import get_source_schedule

        # Get registered sources from orchestrator
        registered_sources = self.orchestrator.get_registered_sources()

        # Create jobs for each enabled source
        for source_name in registered_sources:
            source_config = self.config.get('sources', {}).get(source_name, {})

            if not source_config.get('enabled', False):
                continue

            schedule = get_source_schedule(source_name)

            if not schedule:
                logger.warning(f"No schedule configuration for {source_name}")
                continue

            # Check if source uses cron or interval
            if 'cron' in schedule:
                # Cron-based (e.g., Product Hunt - once a day)
                self._add_cron_job(source_name, schedule)
            else:
                # Interval-based (e.g., HN - different intervals per section)
                self._add_interval_jobs(source_name, schedule)

        logger.info(f"Applied configuration: {len(self.scheduler.get_jobs())} jobs scheduled")

    def _add_interval_jobs(self, source_name: str, schedule: dict):
        """Add interval-based jobs for a source"""
        sections = schedule.get('sections', {})

        for section_name, section_config in sections.items():
            interval_hours = section_config.get('interval_hours', 6)
            limit = section_config.get('limit', 20)

            job_id = f"auto_parse_{source_name}_{section_name}"

            self.scheduler.add_job(
                func=lambda src=source_name, sec=section_name, lim=limit:
                    self._parse_section(src, sec, lim),
                trigger=IntervalTrigger(hours=interval_hours),
                id=job_id,
                name=f"{source_name}/{section_name}",
                replace_existing=True
            )

            logger.info(
                f"Scheduled {source_name}/{section_name}: "
                f"every {interval_hours}h, limit {limit}"
            )

    def _add_cron_job(self, source_name: str, schedule: dict):
        """Add cron-based job for a source"""
        cron_expr = schedule.get('cron')
        limit = schedule.get('limit', 100)

        job_id = f"auto_parse_{source_name}"

        # Parse cron expression (format: "minute hour day month day_of_week")
        parts = cron_expr.split()

        self.scheduler.add_job(
            func=lambda src=source_name, lim=limit:
                self._parse_source_all_sections(src, lim),
            trigger=CronTrigger(
                minute=parts[0],
                hour=parts[1],
                day=parts[2] if len(parts) > 2 else '*',
                month=parts[3] if len(parts) > 3 else '*',
                day_of_week=parts[4] if len(parts) > 4 else '*'
            ),
            id=job_id,
            name=source_name,
            replace_existing=True
        )

        logger.info(f"Scheduled {source_name}: cron {cron_expr}, limit {limit}")

    def _parse_section(self, source_name: str, section: str, limit: int):
        """Parse a specific section of a source"""
        logger.info(f"Auto-parse: {source_name}/{section} starting...")

        try:
            self.orchestrator.parse_source(
                source_name,
                sections=[section],
                limit_per_section=limit
            )

            # Update last parse time
            if 'sources' not in self.config:
                self.config['sources'] = {}
            if source_name not in self.config['sources']:
                self.config['sources'][source_name] = {}

            self.config['sources'][source_name]['last_parse'] = datetime.utcnow().isoformat()
            self._save_config()

            logger.info(f"Auto-parse: {source_name}/{section} completed")

            # Auto-analyze if configured
            if self.config.get('analyze_after_parse') and self.analyze_callback:
                logger.info("Auto-analyze: Starting after parse...")
                self._analyze_job()

        except Exception as e:
            logger.error(f"Auto-parse: {source_name}/{section} failed - {e}")

    def _parse_source_all_sections(self, source_name: str, limit: int):
        """Parse all sections of a source (for cron-based sources)"""
        logger.info(f"Auto-parse: {source_name} (all sections) starting...")

        try:
            self.orchestrator.parse_source(
                source_name,
                sections=None,  # All sections
                limit_per_section=limit
            )

            # Update last parse time
            if 'sources' not in self.config:
                self.config['sources'] = {}
            if source_name not in self.config['sources']:
                self.config['sources'][source_name] = {}

            self.config['sources'][source_name]['last_parse'] = datetime.utcnow().isoformat()
            self._save_config()

            logger.info(f"Auto-parse: {source_name} completed")

            # Auto-analyze if configured
            if self.config.get('analyze_after_parse') and self.analyze_callback:
                logger.info("Auto-analyze: Starting after parse...")
                self._analyze_job()

        except Exception as e:
            logger.error(f"Auto-parse: {source_name} failed - {e}")

    def _analyze_job(self):
        """Execute analysis job"""
        if self.analyze_callback:
            try:
                self.analyze_callback()
                self.config['last_analyze'] = datetime.utcnow().isoformat()
                self._save_config()
                logger.info("Auto-analyze: Completed successfully")
            except Exception as e:
                logger.error(f"Auto-analyze: Failed - {e}")

    def enable_all(self, source_states: dict = None):
        """
        Enable automatic parsing for all or specified sources

        Args:
            source_states: Dict of {source_name: enabled} to set specific states
                          If None, enables all registered sources
        """
        self.config['auto_parse_enabled'] = True

        if 'sources' not in self.config:
            self.config['sources'] = {}

        # Import here to avoid circular dependency
        from parsers.sources_config import get_source_schedule

        if self.orchestrator:
            registered_sources = self.orchestrator.get_registered_sources()

            for source_name in registered_sources:
                schedule = get_source_schedule(source_name)

                if not schedule:
                    continue

                if source_name not in self.config['sources']:
                    self.config['sources'][source_name] = {}

                # Set enabled state
                if source_states and source_name in source_states:
                    enabled = source_states[source_name]
                else:
                    # Use default from schedule config
                    enabled = schedule.get('enabled_by_default', True)

                self.config['sources'][source_name]['enabled'] = enabled

        self._save_config()
        self._apply_config()

        logger.info("Auto-parsing enabled for all sources")

    def disable_all(self):
        """Disable automatic parsing for all sources"""
        self.config['auto_parse_enabled'] = False
        self._save_config()
        self._apply_config()
        logger.info("Auto-parsing disabled")

    def enable_source(self, source_name: str):
        """Enable automatic parsing for a specific source"""
        if 'sources' not in self.config:
            self.config['sources'] = {}

        if source_name not in self.config['sources']:
            self.config['sources'][source_name] = {}

        self.config['sources'][source_name]['enabled'] = True
        self._save_config()

        # Reapply config to add new jobs
        if self.config.get('auto_parse_enabled', False):
            self._apply_config()

        logger.info(f"Source {source_name} enabled")

    def disable_source(self, source_name: str):
        """Disable automatic parsing for a specific source"""
        if 'sources' not in self.config:
            self.config['sources'] = {}

        if source_name not in self.config['sources']:
            self.config['sources'][source_name] = {}

        self.config['sources'][source_name]['enabled'] = False
        self._save_config()

        # Reapply config to remove jobs for this source
        self._apply_config()

        logger.info(f"Source {source_name} disabled")

    def get_status(self) -> dict:
        """Get current scheduler status"""
        jobs = []
        if self.scheduler.running:
            for job in self.scheduler.get_jobs():
                jobs.append({
                    'id': job.id,
                    'name': job.name,
                    'next_run': job.next_run_time.isoformat() if job.next_run_time else None
                })

        # Get source statuses
        sources_status = {}
        if self.orchestrator:
            from parsers.sources_config import get_source_schedule

            for source_name in self.orchestrator.get_registered_sources():
                source_config = self.config.get('sources', {}).get(source_name, {})
                schedule = get_source_schedule(source_name)

                sources_status[source_name] = {
                    'enabled': source_config.get('enabled', False),
                    'last_parse': source_config.get('last_parse'),
                    'schedule': schedule
                }

        return {
            'running': self.scheduler.running,
            'auto_parse_enabled': self.config.get('auto_parse_enabled', False),
            'analyze_after_parse': self.config.get('analyze_after_parse', True),
            'last_analyze': self.config.get('last_analyze'),
            'sources': sources_status,
            'jobs': jobs
        }


# Singleton instance
_scheduler_instance = None

def get_scheduler() -> AutoScheduler:
    """Get or create scheduler instance"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = AutoScheduler()
    return _scheduler_instance
