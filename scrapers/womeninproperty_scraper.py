import re
from datetime import datetime
from .base_scraper import BaseScraper

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


class WomenInPropertyScraper(BaseScraper):
    BASE_URL = "https://www.womeninproperty.org.uk"
    EVENTS_URL = "https://www.womeninproperty.org.uk/events"
    ORGANISATION = "Women in Property"

    def scrape(self) -> list[dict]:
        soup = self.fetch(self.EVENTS_URL)

        seen = set()
        event_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            full = href if href.startswith("http") else self.BASE_URL + href
            # Match branch event URLs and direct /events/YYYY/ URLs
            if (
                "womeninproperty.org.uk" in full
                and "/events/" in full
                and full.rstrip("/") != self.EVENTS_URL.rstrip("/")
                and full not in seen
                and not full.endswith("/events/past")
            ):
                seen.add(full)
                event_links.append(full)

        self.logger.info(f"Found {len(event_links)} Women in Property events")
        return [e for url in event_links if (e := self._parse_event(url))]

    def _parse_event(self, url: str) -> dict | None:
        try:
            soup = self.fetch(url)

            name_tag = soup.find("h1")
            event_name = name_tag.get_text(strip=True) if name_tag else None
            if not event_name:
                event_name = url.rstrip("/").split("/")[-1].replace("-", " ").title()

            start_date = None
            start_time = None
            end_time = None
            location = None

            # Date/time live in <h2>: "Tuesday 21 April 2026 9:15 AM - 10:30 AM"
            for tag in soup.find_all(["h2", "h3", "p", "strong", "span", "div"]):
                text = tag.get_text(strip=True)
                if not text:
                    continue

                if not start_date and any(m in text for m in MONTHS):
                    clean = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", text).strip()
                    # Remove leading weekday "Tuesday "
                    clean = re.sub(r"^[A-Za-z]+day\s+", "", clean).strip()

                    # Try to parse date (first ~20 chars)
                    for fmt in ("%d %B %Y", "%B %d, %Y", "%d %B, %Y"):
                        try:
                            start_date = datetime.strptime(clean[:20], fmt).date().isoformat()
                            break
                        except ValueError:
                            continue

                    # Time from same string: "9:15 AM - 10:30 AM"
                    t_match = re.search(
                        r"(\d+:\d+\s*(?:AM|PM))\s*[-–]\s*(\d+:\d+\s*(?:AM|PM))",
                        text, re.IGNORECASE,
                    )
                    if t_match:
                        start_time = t_match.group(1).lower()
                        end_time = t_match.group(2).lower()
                    elif not start_time:
                        single = re.search(r"\d+:\d+\s*(AM|PM)", text, re.IGNORECASE)
                        if single:
                            start_time = single.group(0).lower()

                # Location: text after the date/time heading
                if start_date and not location:
                    # Next sibling <p> or <div> that looks like an address
                    for sibling in tag.find_next_siblings(["p", "div", "span"]):
                        loc_text = sibling.get_text(strip=True)
                        if loc_text and len(loc_text) < 200 and not re.search(r"\d+:\d+", loc_text):
                            location = loc_text
                            break

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
                "sector_tag": "Women in Property",
                "link": url,
                "description": description,
            }

        except Exception as e:
            self.logger.error(f"Failed to parse Women in Property event {url}: {e}")
            return None
