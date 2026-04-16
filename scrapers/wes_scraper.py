import re
from datetime import datetime
from .base_scraper import BaseScraper

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


class WESScraper(BaseScraper):
    BASE_URL = "https://www.wes.org.uk"
    EVENTS_URL = "https://www.wes.org.uk/events/"
    ORGANISATION = "Women's Engineering Society"

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

        self.logger.info(f"Found {len(event_links)} WES events")
        events = []
        for url in event_links:
            event = self._parse_event(url)
            if event:
                events.append(event)
        return events

    def _parse_event(self, url: str) -> dict | None:
        try:
            soup = self.fetch(url)

            # Event name
            name_tag = soup.find("h1")
            event_name = name_tag.get_text(strip=True) if name_tag else None
            if not event_name:
                slug = url.rstrip("/").split("/")[-1]
                event_name = slug.replace("-", " ").title()

            start_date = None
            start_time = None
            end_time = None

            # Date — WES puts dates in <strong> inside paragraphs
            for tag in soup.find_all(["strong", "h3", "h4", "p", "span", "time"]):
                text = tag.get_text(strip=True)
                if not text:
                    continue

                if not start_date and any(m in text for m in MONTHS):
                    clean = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", text).strip()
                    # Handle ranges like "16-17 April 2026"
                    clean = re.sub(r"(\d+)-\d+\s", r"\1 ", clean)
                    for fmt in ("%d %B %Y", "%B %d, %Y", "%d %B"):
                        try:
                            parsed = datetime.strptime(clean[:20], fmt)
                            start_date = parsed.date().isoformat()
                            break
                        except ValueError:
                            continue

                if not start_time and re.search(r"\d+(:\d+)?\s*(am|pm)", text, re.IGNORECASE):
                    rng = re.match(
                        r"(\d+(?::\d+)?)\s*(am|pm)\s*[-–]\s*(\d+(?::\d+)?)\s*(am|pm)",
                        text, re.IGNORECASE,
                    )
                    if rng:
                        start_time = f"{rng.group(1)} {rng.group(2)}".lower()
                        end_time = f"{rng.group(3)} {rng.group(4)}".lower()
                    else:
                        single = re.search(r"\d+(?::\d+)?\s*(am|pm)", text, re.IGNORECASE)
                        if single:
                            start_time = single.group(0).strip().lower()

            # Location — WES uses <h3> followed by address paragraph
            location = None
            for h3 in soup.find_all("h3"):
                h3_text = h3.get_text(strip=True).lower()
                if any(kw in h3_text for kw in ["location", "venue", "where", "address"]):
                    nxt = h3.find_next_sibling("p")
                    if nxt:
                        location = nxt.get_text(strip=True)
                    break

            # Fallback: look for postcode pattern (UK addresses)
            if not location:
                for p in soup.find_all("p"):
                    text = p.get_text(strip=True)
                    if re.search(r"\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b", text):
                        location = text[:150]
                        break

            # Description
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
                "event_type": "Engineering Event",
                "sector_tag": "Women in Engineering",
                "link": url,
                "description": description,
            }

        except Exception as e:
            self.logger.error(f"Failed to parse WES event {url}: {e}")
            return None
