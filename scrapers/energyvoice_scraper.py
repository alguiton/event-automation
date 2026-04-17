import re
from datetime import datetime
from .base_scraper import BaseScraper

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


class EnergyVoiceScraper(BaseScraper):
    """Scraper for the Women in New Energy event on Energy Voice."""

    PAGE_URL = "https://content.energyvoice.com/women-in-new-energy/"
    ORGANISATION = "Energy Voice"

    def scrape(self) -> list[dict]:
        soup = self.fetch(self.PAGE_URL)

        # Event name
        h2 = soup.find("h2")
        event_name = h2.get_text(strip=True) if h2 else "Women in New Energy"

        start_date = None
        start_time = None
        end_time = None
        location = None

        # Date/time/location are in a <p> like:
        # "Tuesday 23rd June 2026 | P&J Live, Aberdeen | 08:45 – 16:30"
        for tag in soup.find_all(["p", "h3", "span", "div"]):
            text = tag.get_text(strip=True)
            if not text:
                continue

            if not start_date and any(m in text for m in MONTHS):
                # Split on "|" to get date, location, time parts
                parts = [p.strip() for p in text.split("|")]
                for part in parts:
                    clean = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", part).strip()
                    clean = re.sub(r"^[A-Za-z]+day\s+", "", clean).strip()
                    if not start_date and any(m in clean for m in MONTHS):
                        for fmt in ("%d %B %Y", "%B %d, %Y"):
                            try:
                                start_date = datetime.strptime(clean[:20], fmt).date().isoformat()
                                break
                            except ValueError:
                                continue

                    # Location part: contains a place name but no time digits
                    if not location and not re.search(r"\d+:\d+", part) and not any(m in part for m in MONTHS):
                        if len(part) > 3:
                            location = part.strip()

                    # Time part: "08:45 – 16:30"
                    if not start_time and re.search(r"\d+:\d+", part):
                        t_match = re.match(
                            r"(\d+:\d+)\s*[-–]\s*(\d+:\d+)", part.strip()
                        )
                        if t_match:
                            start_time = t_match.group(1)
                            end_time = t_match.group(2)

                if start_date:
                    break

        description = None
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if len(text) > 80:
                description = text[:500]
                break

        if not start_date:
            self.logger.warning("EnergyVoice: could not parse date from page.")
            return []

        return [{
            "event_name": event_name,
            "organisation": self.ORGANISATION,
            "start_date": start_date,
            "start_time": start_time,
            "end_time": end_time,
            "location": location,
            "event_type": "Conference",
            "sector_tag": "Women in Energy",
            "link": self.PAGE_URL,
            "description": description,
        }]
