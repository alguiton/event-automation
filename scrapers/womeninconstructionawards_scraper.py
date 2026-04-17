import re
from datetime import datetime
from .base_scraper import BaseScraper

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


class WomenInConstructionAwardsScraper(BaseScraper):
    """Scraper for the Women in Construction Awards annual ceremony."""

    PAGE_URL = "https://womeninconstructionawards.com/women-in-construction-awards-2026/"
    ORGANISATION = "Women in Construction Awards"

    def scrape(self) -> list[dict]:
        soup = self.fetch(self.PAGE_URL)

        name_tag = soup.find("h1") or soup.find("h2")
        event_name = name_tag.get_text(strip=True) if name_tag else "Women in Construction Awards 2026"

        start_date = None
        location = None

        # Page contains "29th October 2026" and "Royal Lancaster London"
        for tag in soup.find_all(["h1", "h2", "h3", "p", "span", "div", "strong", "li"]):
            text = tag.get_text(strip=True)
            if not text:
                continue

            if not start_date and any(m in text for m in MONTHS):
                clean = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", text).strip()
                for fmt in ("%d %B %Y", "%B %d, %Y"):
                    try:
                        start_date = datetime.strptime(clean[:20], fmt).date().isoformat()
                        break
                    except ValueError:
                        continue

            if not location and any(kw in text.lower() for kw in [
                "hotel", "london", "venue", "royal", "lancaster",
            ]):
                if len(text) < 150 and not any(m in text for m in MONTHS):
                    location = text

        description = None
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if len(text) > 60:
                description = text[:500]
                break

        if not start_date:
            self.logger.warning("WiCA: could not parse date from page.")
            return []

        return [{
            "event_name": event_name,
            "organisation": self.ORGANISATION,
            "start_date": start_date,
            "start_time": None,
            "end_time": None,
            "location": location,
            "event_type": "Awards Ceremony",
            "sector_tag": "Women in Construction",
            "link": self.PAGE_URL,
            "description": description,
        }]
