from abc import ABC, abstractmethod
import requests
from bs4 import BeautifulSoup
from utils.logger import get_logger
from utils.db import get_supabase_client


class BaseScraper(ABC):
    """Base class for all event scrapers."""

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.db = get_supabase_client()

    def fetch(self, url: str, headers: dict = None) -> BeautifulSoup:
        """Fetch a URL and return a BeautifulSoup object."""
        self.logger.info(f"Fetching {url}")
        response = requests.get(url, timeout=15, headers=headers)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")

    @abstractmethod
    def scrape(self) -> list[dict]:
        """Scrape events and return a list of event dicts."""
        pass

    def save(self, events: list[dict], table: str = "events"):
        """Delete existing rows for this organisation then insert fresh data."""
        if not events:
            self.logger.info("No events to save.")
            return
        # Drop rows missing required fields to avoid NOT NULL violations
        valid = [e for e in events if e.get("event_name")]
        skipped = len(events) - len(valid)
        if skipped:
            self.logger.warning(f"Skipping {skipped} events with missing event_name.")
        if not valid:
            self.logger.info("No valid events to save.")
            return
        # Delete old rows for this organisation so stale data is always replaced
        org = valid[0].get("organisation")
        if org:
            self.logger.info(f"Deleting existing rows for organisation: {org}")
            self.db.table(table).delete().eq("organisation", org).execute()
        self.logger.info(f"Inserting {len(valid)} events into {table}...")
        self.db.table(table).insert(valid).execute()

    def run(self):
        """Full pipeline: scrape then save."""
        events = self.scrape()
        self.save(events)
