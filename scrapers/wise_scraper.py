import re
from datetime import date, datetime
from .base_scraper import BaseScraper

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}


class WISEScraper(BaseScraper):
    BASE_URL = "https://www.wisecampaign.org.uk"
    EVENTS_URL = "https://www.wisecampaign.org.uk/events/"
    ORGANISATION = "WISE Campaign"

    def scrape(self) -> list[dict]:
        """Parse WISE events directly from the listing page."""
        soup = self.fetch(self.EVENTS_URL)
        today = date.today()

        events = []
        # The listing page shows: "Month Day @ HH:MM am - HH:MM am" then h3>a for title
        # Walk all text nodes looking for the date/time pattern
        for tag in soup.find_all(string=re.compile(r"\w+ \d+ @ \d+:\d+", re.IGNORECASE)):
            text = tag.strip()
            m = re.match(
                r"(\w+)\s+(\d+)\s*@\s*(\d+:\d+)\s*(am|pm)\s*[-–]\s*(\d+:\d+)\s*(am|pm)",
                text, re.IGNORECASE,
            )
            if not m:
                continue

            month_str = m.group(1).lower()
            if month_str not in MONTHS:
                continue

            month_num = MONTHS[month_str]
            day = int(m.group(2))
            year = today.year if month_num >= today.month else today.year + 1

            try:
                event_date = date(year, month_num, day)
            except ValueError:
                continue

            # Skip past events
            if event_date < today:
                continue

            start_time = f"{m.group(3)} {m.group(4)}".lower()
            end_time = f"{m.group(5)} {m.group(6)}".lower()

            # Find the nearest h3 > a after this text node for title + link
            parent = tag.parent
            event_name = None
            link = None
            for sibling in parent.find_next_siblings():
                a = sibling.find("a") if sibling.name != "a" else sibling
                h3 = sibling if sibling.name == "h3" else sibling.find("h3")
                if h3:
                    a = h3.find("a") or a
                if a and a.get("href"):
                    event_name = a.get_text(strip=True)
                    href = a["href"]
                    link = href if href.startswith("http") else self.BASE_URL + href
                    break
                # Stop if we hit another date pattern
                if re.search(r"\w+ \d+ @ \d+:\d+", sibling.get_text(), re.IGNORECASE):
                    break

            if not event_name or not link:
                continue

            # Location — scan the next few siblings for ONLINE, venue, etc.
            location = None
            for sibling in parent.find_next_siblings():
                stext = sibling.get_text(strip=True)
                if not stext or len(stext) > 300:
                    continue
                # Stop at next event block
                if re.search(r"\w+ \d+ @ \d+:\d+", stext, re.IGNORECASE):
                    break
                if any(kw in stext.upper() for kw in ["ONLINE", "VIRTUAL", "ZOOM"]):
                    location = "Online"
                    break
                # IET venue pattern
                if "IET" in stext or re.search(r"\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b", stext):
                    location = stext[:150]
                    break

            # Description — first substantial paragraph after title
            description = None
            for sibling in parent.find_next_siblings():
                stext = sibling.get_text(strip=True)
                if len(stext) > 80 and not re.search(r"\w+ \d+ @ \d+:\d+", stext):
                    description = stext[:500]
                    break

            events.append({
                "event_name": event_name,
                "organisation": self.ORGANISATION,
                "start_date": event_date.isoformat(),
                "start_time": start_time,
                "end_time": end_time,
                "location": location,
                "event_type": "STEM Event",
                "sector_tag": "Women in STEM",
                "link": link,
                "description": description,
            })

        self.logger.info(f"Found {len(events)} WISE events")
        return events
