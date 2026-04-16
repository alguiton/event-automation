from .base_scraper import BaseScraper
from .wun_scraper import WUNScraper
from .powerfulwomen_scraper import PowerfulWomenScraper
from .stemazing_scraper import STEmazingScraper


def run_all_scrapers():
    """Run all scrapers in sequence."""
    for ScraperClass in [WUNScraper, PowerfulWomenScraper, STEmazingScraper]:
        try:
            ScraperClass().run()
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"{ScraperClass.__name__} failed: {e}")
