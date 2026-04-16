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

    def fetch(self, url: str) -> BeautifulSoup:
        """Fetch a URL and return a BeautifulSoup object."""
        self.logger.info(f"Fetching {url}")
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")

    @abstractmethod
    def scrape(self) -> list[dict]:
        """Scrape events and return a list of event dicts."""
        pass

    def save(self, events: list[dict], table: str = "events"):
        """Upsert events into Supabase."""
        if not events:
            self.logger.info("No events to save.")
            return
        self.logger.info(f"Saving {len(events)} events to {table}...")
        self.db.table(table).upsert(events).execute()

    def run(self):
        """Full pipeline: scrape then save."""
        events = self.scrape()
        self.save(events)
