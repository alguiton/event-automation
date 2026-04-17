from .base_scraper import BaseScraper
from .wun_scraper import WUNScraper
from .powerfulwomen_scraper import PowerfulWomenScraper
from .stemazing_scraper import STEmazingScraper
from .wise_scraper import WISEScraper
from .wes_scraper import WESScraper
from .winuk_scraper import WiNUKScraper
from .stemwomen_scraper import STEMWomenScraper
from .energyvoice_scraper import EnergyVoiceScraper
from .womeninproperty_scraper import WomenInPropertyScraper
from .renewableni_scraper import RenewableNIScraper
from .womeninrail_scraper import WomenInRailScraper
from .womeninsustainability_scraper import WomenInSustainabilityScraper
from .bcswomen_scraper import BCSWomenScraper
from .womenintransport_scraper import WomenInTransportScraper
from .womeninconstructionawards_scraper import WomenInConstructionAwardsScraper
from .afbe_scraper import AFBEScraper


def run_all_scrapers():
    """Run all scrapers in sequence."""
    scrapers = [
        WUNScraper,
        PowerfulWomenScraper,
        STEmazingScraper,
        WISEScraper,
        WESScraper,
        WiNUKScraper,
        STEMWomenScraper,
        EnergyVoiceScraper,
        WomenInPropertyScraper,
        RenewableNIScraper,
        WomenInRailScraper,
        WomenInSustainabilityScraper,
        BCSWomenScraper,
        WomenInTransportScraper,
        WomenInConstructionAwardsScraper,
        AFBEScraper,
    ]
    for ScraperClass in scrapers:
        try:
            ScraperClass().run()
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"{ScraperClass.__name__} failed: {e}")
