import re
from datetime import datetime
from .base_scraper import BaseScraper

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


class WISEScraper(BaseScraper):
    BASE_URL = "https://www.wisecampaign.org.uk"
    EVENTS_URL = "https://www.wisecampaign.org.uk/events/"
    ORGANISATION = "WISE Campaign"

    def scrape(self) -> list[dict]:
        soup = self.fetch(self.EVENTS_URL)

        seen = set()
        event_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            full = href if href.startswith("http") else self.BASE_URL + href
            # WISE uses /event/ (singular) for individual pages
            if (
                "/event/" in full
                and full not in seen
            ):
                seen.add(full)
                event_links.append(full)

        self.logger.info(f"Found {len(event_links)} WISE events")
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
            name_tag = soup.find("h1") or soup.find("h2")
            event_name = name_tag.get_text(strip=True) if name_tag else None
            if not event_name:
                slug = url.rstrip("/").split("/")[-1]
                event_name = slug.replace("-", " ").title()

            start_date = None
            start_time = None
            end_time = None
            location = None

            for tag in soup.find_all(["h2", "h3", "h4", "p", "span", "time", "li", "div"]):
                text = tag.get_text(strip=True)
                if not text or len(text) > 200:
                    continue

                # Date
                if not start_date and any(m in text for m in MONTHS):
                    clean = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", text).strip()
                    for fmt in ("%d %B %Y", "%B %d, %Y", "%d %B", "%B %d"):
                        try:
                            parsed = datetime.strptime(clean[:20], fmt)
                            start_date = parsed.date().isoformat()
                            break
                        except ValueError:
                            continue

                # Time range "9:30 am - 4:30 pm"
                if not start_time and re.search(r"\d+:\d+\s*(am|pm)", text, re.IGNORECASE):
                    rng = re.match(
                        r"(\d+:\d+)\s*(am|pm)\s*[-–]\s*(\d+:\d+)\s*(am|pm)",
                        text, re.IGNORECASE,
                    )
                    if rng:
                        start_time = f"{rng.group(1)} {rng.group(2)}".lower()
                        end_time = f"{rng.group(3)} {rng.group(4)}".lower()
                    else:
                        single = re.search(r"\d+:\d+\s*(am|pm)", text, re.IGNORECASE)
                        if single:
                            start_time = single.group(0).strip().lower()

            # Location — look for a tag labelled "Location" or "Venue"
            for tag in soup.find_all(["h3", "h4", "strong", "dt"]):
                if tag.get_text(strip=True).lower() in ("location", "venue", "where"):
                    nxt = tag.find_next_sibling()
                    if nxt:
                        location = nxt.get_text(strip=True)
                    break

            # Fallback: scan for address-like content or online/virtual
            if not location:
                for tag in soup.find_all(["p", "span", "li", "dd"]):
                    text = tag.get_text(strip=True)
                    if not text or len(text) > 150:
                        continue
                    if any(kw in text.lower() for kw in ["online", "virtual", "zoom", "teams"]):
                        location = text
                        break
                    # Simple heuristic: contains comma and looks like an address
                    if "," in text and re.search(r"\b[A-Z]{1,2}\d", text):
                        location = text
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
                "event_type": "STEM Event",
                "sector_tag": "Women in STEM",
                "link": url,
                "description": description,
            }

        except Exception as e:
            self.logger.error(f"Failed to parse WISE event {url}: {e}")
            return None
