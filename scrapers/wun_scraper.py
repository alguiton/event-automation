import re
from datetime import datetime
from .base_scraper import BaseScraper


class WUNScraper(BaseScraper):
    BASE_URL = "https://thewun.co.uk"
    EVENTS_URL = "https://thewun.co.uk/events/"
    ORGANISATION = "The WUN"

    def scrape(self) -> list[dict]:
        soup = self.fetch(self.EVENTS_URL)

        # Collect unique event detail URLs
        seen = set()
        event_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            full = href if href.startswith("http") else self.BASE_URL + href
            # Keep only individual event pages, not the listing page itself
            if (
                "/events/" in full
                and full.rstrip("/") != self.EVENTS_URL.rstrip("/")
                and full not in seen
            ):
                seen.add(full)
                event_links.append(full)

        self.logger.info(f"Found {len(event_links)} WUN events")
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
            h2 = soup.find("h2")
            event_name = h2.get_text(strip=True) if h2 else None

            # Date and time live in <h4> tags
            start_date = None
            start_time = None
            end_time = None

            months = [
                "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December",
            ]

            for h4 in soup.find_all("h4"):
                text = h4.get_text(strip=True)

                # Date: "27th April 2026"
                if any(m in text for m in months):
                    clean = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", text).strip()
                    try:
                        start_date = datetime.strptime(clean, "%d %B %Y").date().isoformat()
                    except ValueError:
                        pass

                # Time: "12-1:30 pm" or "12:00 pm" etc.
                elif re.search(r"\d+[\s:-]", text) and re.search(r"(am|pm)", text, re.IGNORECASE):
                    # Range: "12-1:30 pm" or "12:00-13:30"
                    rng = re.match(
                        r"(\d+(?::\d+)?)\s*[-–]\s*(\d+(?::\d+)?)\s*(am|pm)?",
                        text,
                        re.IGNORECASE,
                    )
                    if rng:
                        start_time = rng.group(1)
                        end_time = f"{rng.group(2)} {rng.group(3) or ''}".strip()
                    else:
                        start_time = text

            # Location: first text node after <h3>Location</h3>
            location = "Online"
            for h3 in soup.find_all("h3"):
                if "location" in h3.get_text(strip=True).lower():
                    nxt = h3.find_next_sibling()
                    if nxt:
                        location = nxt.get_text(strip=True)
                    break

            # Description: paragraphs after <h3>Information</h3>
            description = None
            for h3 in soup.find_all("h3"):
                if "information" in h3.get_text(strip=True).lower():
                    parts = []
                    for p in h3.find_next_siblings("p"):
                        parts.append(p.get_text(strip=True))
                        if len(parts) >= 3:
                            break
                    description = " ".join(parts) or None
                    break

            return {
                "event_name": event_name,
                "organisation": self.ORGANISATION,
                "start_date": start_date,
                "start_time": start_time,
                "end_time": end_time,
                "location": location,
                "event_type": "Workshop / Event",
                "sector_tag": "Women in Business",
                "link": url,
                "description": description,
            }

        except Exception as e:
            self.logger.error(f"Failed to parse WUN event {url}: {e}")
            return None
