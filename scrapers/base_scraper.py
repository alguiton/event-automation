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
        from datetime import date
        today = date.today()
        # Drop rows missing required fields or with no/past date
        valid = []
        for e in events:
            if not e.get("event_name"):
                self.logger.warning(f"Skipping event with no name: {e.get('link')}")
                continue
            if not e.get("start_date"):
                self.logger.warning(f"Skipping event with no date: {e.get('event_name')}")
                continue
            try:
                if date.fromisoformat(e["start_date"]) < today:
                    self.logger.info(f"Skipping past event: {e.get('event_name')} ({e['start_date']})")
                    continue
            except ValueError:
                self.logger.warning(f"Skipping event with invalid date: {e.get('event_name')}")
                continue
            valid.append(e)
        skipped = len(events) - len(valid)
        if skipped:
            self.logger.warning(f"Skipped {skipped} events (no name, no date, or past).")
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
