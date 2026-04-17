import re
from datetime import datetime
from .base_scraper import BaseScraper

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


class AFBEScraper(BaseScraper):
    BASE_URL = "https://www.afbe.org.uk"
    EVENTS_URL = "https://www.afbe.org.uk/events"
    ORGANISATION = "AFBE-UK"

    def scrape(self) -> list[dict]:
        soup = self.fetch(self.EVENTS_URL)

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

        self.logger.info(f"Found {len(event_links)} AFBE events")
        return [e for url in event_links if (e := self._parse_event(url))]

    def _parse_event(self, url: str) -> dict | None:
        try:
            soup = self.fetch(url)

            name_tag = soup.find("h1") or soup.find("h2") or soup.find("h3")
            event_name = name_tag.get_text(strip=True) if name_tag else None
            if not event_name:
                event_name = url.rstrip("/").split("/")[-1].replace("-", " ").replace("_", " ").title()

            start_date = None
            start_time = None
            end_time = None
            location = None

            for tag in soup.find_all(["p", "h3", "h4", "span", "div", "li", "strong", "time"]):
                text = tag.get_text(strip=True)
                if not text:
                    continue

                if not start_date and any(m in text for m in MONTHS):
                    clean = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", text).strip()
                    clean = re.sub(r"^[A-Za-z]+day,?\s+", "", clean).strip()
                    for fmt in ("%d %B %Y", "%B %d, %Y", "%B %d %Y"):
                        try:
                            start_date = datetime.strptime(clean[:20], fmt).date().isoformat()
                            break
                        except ValueError:
                            continue

                if not start_time and re.search(r"\d+(?::\d+)?\s*(am|pm)", text, re.IGNORECASE):
                    rng = re.match(
                        r"(\d+(?::\d+)?\s*(?:am|pm))\s*[-–]\s*(\d+(?::\d+)?\s*(?:am|pm))",
                        text, re.IGNORECASE,
                    )
                    if rng:
                        start_time = rng.group(1).lower().strip()
                        end_time = rng.group(2).lower().strip()
                    else:
                        single = re.search(r"\d+(?::\d+)?\s*(am|pm)", text, re.IGNORECASE)
                        if single:
                            start_time = single.group(0).lower().strip()

                if not location and len(text) < 150:
                    lower = text.lower()
                    if any(kw in lower for kw in ["online", "virtual", "zoom", "teams", "webinar"]):
                        location = "Online"
                    elif any(kw in lower for kw in ["venue", "hotel", "street", "road", "hall", "centre"]):
                        location = text

            description = None
            for p in soup.find_all("p"):
                text = p.get_text(strip=True)
                if len(text) > 60:
                    description = text[:500]
                    break

            return {
                "event_name": event_name,
                "organisation": self.ORGANISATION,
                "start_date": start_date,
                "start_time": start_time,
                "end_time": end_time,
                "location": location,
                "event_type": "Networking / Event",
                "sector_tag": "Black Engineers",
                "link": url,
                "description": description,
            }

        except Exception as e:
            self.logger.error(f"Failed to parse AFBE event {url}: {e}")
            return None
