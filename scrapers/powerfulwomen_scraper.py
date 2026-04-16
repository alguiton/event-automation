import re
from datetime import datetime
from .base_scraper import BaseScraper

# powerfulwomen.org.uk returns 403 for default requests.
# We send browser-like headers to work around the block.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.5",
    "Referer": "https://powerfulwomen.org.uk/",
}

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


class PowerfulWomenScraper(BaseScraper):
    BASE_URL = "https://powerfulwomen.org.uk"
    EVENTS_URL = "https://powerfulwomen.org.uk/events/"
    ORGANISATION = "Powerful Women"

    def scrape(self) -> list[dict]:
        soup = self.fetch(self.EVENTS_URL, headers=HEADERS)

        seen = set()
        event_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            full = href if href.startswith("http") else self.BASE_URL + href
            if (
                "/events/" in full
                and full.rstrip("/") != self.EVENTS_URL.rstrip("/")
                and full not in seen
            ):
                seen.add(full)
                event_links.append(full)

        self.logger.info(f"Found {len(event_links)} Powerful Women events")
        events = []
        for url in event_links:
            event = self._parse_event(url)
            if event:
                events.append(event)
        return events

    def _parse_event(self, url: str) -> dict | None:
        try:
            soup = self.fetch(url, headers=HEADERS)

            # Event name — try h1 first, then h2
            name_tag = soup.find("h1") or soup.find("h2")
            event_name = name_tag.get_text(strip=True) if name_tag else None

            # Date and time — scan all text nodes for recognisable patterns
            start_date = None
            start_time = None
            end_time = None

            for tag in soup.find_all(["h2", "h3", "h4", "p", "span", "time"]):
                text = tag.get_text(strip=True)

                if not start_date and any(m in text for m in MONTHS):
                    clean = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", text).strip()
                    # Try various date formats
                    for fmt in ("%d %B %Y", "%B %d %Y", "%d %B", "%B %d"):
                        try:
                            parsed = datetime.strptime(clean[:20], fmt)
                            start_date = parsed.date().isoformat()
                            break
                        except ValueError:
                            continue

                if not start_time and re.search(r"\d+(:\d+)?\s*(am|pm)", text, re.IGNORECASE):
                    rng = re.match(
                        r"(\d+(?::\d+)?)\s*(am|pm)?\s*[-–]\s*(\d+(?::\d+)?)\s*(am|pm)?",
                        text,
                        re.IGNORECASE,
                    )
                    if rng:
                        start_time = f"{rng.group(1)} {rng.group(2) or ''}".strip()
                        end_time = f"{rng.group(3)} {rng.group(4) or ''}".strip()
                    else:
                        single = re.search(r"\d+(?::\d+)?\s*(am|pm)", text, re.IGNORECASE)
                        if single:
                            start_time = single.group(0).strip()

            # Location
            location = "Online"
            for tag in soup.find_all(["p", "span", "div"]):
                text = tag.get_text(strip=True).lower()
                if "location" in text or "venue" in text or "online" in text or "virtual" in text:
                    location = tag.get_text(strip=True)
                    break

            # Description — first substantial paragraph
            description = None
            for p in soup.find_all("p"):
                text = p.get_text(strip=True)
                if len(text) > 80:
                    description = text[:500]
                    break

            return {
                "event_name": event_name,
                "organisation": self.ORGANISATION,
                "start_date": start_date,
                "start_time": start_time,
                "end_time": end_time,
                "location": location,
                "event_type": "Conference / Event",
                "sector_tag": "Women in Energy",
                "link": url,
                "description": description,
            }

        except Exception as e:
            self.logger.error(f"Failed to parse Powerful Women event {url}: {e}")
            return None
