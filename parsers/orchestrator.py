"""
Parser Orchestrator - manages multiple parsers

Coordinates parsing from multiple sources:
- Hacker News
- Reddit (future)
- Product Hunt (future)
- etc.
"""
from typing import Dict, List, Optional
from datetime import datetime
import threading
from loguru import logger

from storage.universal_database import UniversalDatabaseManager
from parsers.base_parser import BaseParser


class ParserOrchestrator:
    """
    Orchestrates parsing from multiple sources

    Features:
    - Manages multiple parsers
    - Can parse all sources or specific source
    - Parallel parsing support
    - Error handling and recovery
    """

    def __init__(self, db: UniversalDatabaseManager):
        """
        Initialize orchestrator

        Args:
            db: Database manager instance
        """
        self.db = db
        self.parsers: Dict[str, BaseParser] = {}
        self.status = {
            'is_running': False,
            'current_source': None,
            'current_section': None,
            'last_run': None,
            'errors': []
        }

    def register_parser(self, parser: BaseParser):
        """
        Register a parser

        Args:
            parser: Parser instance inheriting from BaseParser
        """
        self.parsers[parser.source_name] = parser
        logger.info(f"Registered parser: {parser.source_name}")

    def get_registered_sources(self) -> List[str]:
        """Get list of registered source names"""
        return list(self.parsers.keys())

    def parse_source(self, source_name: str, sections: Optional[List[str]] = None,
                    limit_per_section: int = 20) -> Dict[str, int]:
        """
        Parse a specific source

        Args:
            source_name: Name of source to parse
            sections: List of sections to parse (None = all available)
            limit_per_section: Items to fetch per section

        Returns:
            Dict with section -> items_count
        """
        parser = self.parsers.get(source_name)
        if not parser:
            raise ValueError(f"Parser not registered: {source_name}")

        self.status['current_source'] = source_name
        results = {}

        # Get sections to parse
        if sections is None:
            sections = parser.get_available_sections()

        logger.info(f"Parsing {source_name}: {sections}")

        for section in sections:
            self.status['current_section'] = section

            try:
                # Use BaseParser's parse_and_save method
                items_count = parser.parse_and_save(self.db, section, limit_per_section)
                results[section] = items_count

                logger.info(f"✓ {source_name}/{section}: {items_count} items")

            except Exception as e:
                logger.error(f"✗ {source_name}/{section}: {str(e)}")
                self.status['errors'].append({
                    'source': source_name,
                    'section': section,
                    'error': str(e),
                    'timestamp': datetime.utcnow()
                })
                results[section] = 0

        self.status['current_source'] = None
        self.status['current_section'] = None

        return results

    def parse_all(self, limit_per_section: int = 20, parallel: bool = False) -> Dict[str, Dict[str, int]]:
        """
        Parse all registered sources

        Args:
            limit_per_section: Items to fetch per section
            parallel: If True, parse sources in parallel (experimental)

        Returns:
            Dict with source -> {section -> items_count}
        """
        if self.status['is_running']:
            raise RuntimeError("Parsing already in progress")

        self.status['is_running'] = True
        self.status['last_run'] = datetime.utcnow()
        self.status['errors'] = []

        all_results = {}

        try:
            if parallel and len(self.parsers) > 1:
                # Parallel parsing
                all_results = self._parse_parallel(limit_per_section)
            else:
                # Sequential parsing
                for source_name in self.parsers:
                    try:
                        results = self.parse_source(source_name, limit_per_section=limit_per_section)
                        all_results[source_name] = results
                    except Exception as e:
                        logger.error(f"Failed to parse {source_name}: {e}")
                        all_results[source_name] = {'error': str(e)}

        finally:
            self.status['is_running'] = False
            self.status['current_source'] = None
            self.status['current_section'] = None

        return all_results

    def _parse_parallel(self, limit_per_section: int) -> Dict[str, Dict[str, int]]:
        """
        Parse multiple sources in parallel using threads

        Args:
            limit_per_section: Items per section

        Returns:
            Combined results from all sources
        """
        results = {}
        threads = []

        def parse_thread(source_name: str):
            try:
                results[source_name] = self.parse_source(source_name, limit_per_section=limit_per_section)
            except Exception as e:
                logger.error(f"Thread error for {source_name}: {e}")
                results[source_name] = {'error': str(e)}

        # Start threads for each source
        for source_name in self.parsers:
            thread = threading.Thread(target=parse_thread, args=(source_name,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        return results

    def get_status(self) -> Dict:
        """Get current orchestrator status"""
        return {
            'is_running': self.status['is_running'],
            'current_source': self.status['current_source'],
            'current_section': self.status['current_section'],
            'last_run': self.status['last_run'],
            'registered_sources': self.get_registered_sources(),
            'recent_errors': self.status['errors'][-5:] if self.status['errors'] else []
        }

    def get_stats_summary(self) -> Dict:
        """Get summary statistics across all sources"""
        stats = self.db.get_stats()

        # Add per-source breakdown
        source_breakdown = {}
        for source_name in self.parsers:
            source_breakdown[source_name] = {
                'posts': stats.get(f'{source_name}_posts', 0),
                'parser': self.parsers[source_name].__class__.__name__
            }

        return {
            'total_stats': stats,
            'by_source': source_breakdown,
            'registered_parsers': len(self.parsers)
        }


# Convenience function
def create_orchestrator(db: UniversalDatabaseManager) -> ParserOrchestrator:
    """
    Create orchestrator with default parsers

    Args:
        db: Database manager

    Returns:
        ParserOrchestrator with parsers registered
    """
    orchestrator = ParserOrchestrator(db)

    # Register HN parser
    try:
        from parsers.hacker_news.refactored_parser import HackerNewsParser
        hn_parser = HackerNewsParser()
        orchestrator.register_parser(hn_parser)
        logger.info("✓ Hacker News parser registered")
    except Exception as e:
        logger.error(f"✗ Failed to register HN parser: {e}")

    # Register Reddit parser
    try:
        from parsers.reddit.parser import RedditParser
        reddit_parser = RedditParser()
        orchestrator.register_parser(reddit_parser)
        logger.info("✓ Reddit parser registered")
    except Exception as e:
        logger.error(f"✗ Failed to register Reddit parser: {e}")

    # Register Product Hunt parser
    try:
        from parsers.product_hunt.parser import ProductHuntParser
        ph_parser = ProductHuntParser()
        orchestrator.register_parser(ph_parser)
        logger.info("✓ Product Hunt parser registered")
    except Exception as e:
        logger.error(f"✗ Failed to register Product Hunt parser: {e}")

    # Register Dev.to parser
    try:
        from parsers.devto.parser import DevToParser
        devto_parser = DevToParser()
        orchestrator.register_parser(devto_parser)
        logger.info("✓ Dev.to parser registered")
    except Exception as e:
        logger.error(f"✗ Failed to register Dev.to parser: {e}")

    # Register VC Blogs parser
    try:
        from parsers.vc_blogs.parser import VCBlogsParser
        vc_parser = VCBlogsParser()
        orchestrator.register_parser(vc_parser)
        logger.info("✓ VC Blogs parser registered")
    except Exception as e:
        logger.error(f"✗ Failed to register VC Blogs parser: {e}")

    # Register TechCrunch parser
    try:
        from parsers.techcrunch.parser import TechCrunchParser
        tc_parser = TechCrunchParser()
        orchestrator.register_parser(tc_parser)
        logger.info("✓ TechCrunch parser registered")
    except Exception as e:
        logger.error(f"✗ Failed to register TechCrunch parser: {e}")

    # Future: Register other parsers
    # try:
    #     from parsers.twitter.parser import TwitterParser
    #     twitter_parser = TwitterParser()
    #     orchestrator.register_parser(twitter_parser)
    # except Exception as e:
    #     logger.error(f"Failed to register Twitter parser: {e}")

    return orchestrator
