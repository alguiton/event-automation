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

    def _parse_time_range(self, text: str):
        """Parse a time string into (start_time, end_time). Returns (str|None, str|None)."""
        # Normalise "Noon" → "12:00 pm"
        text = re.sub(r"\bnoon\b", "12:00 pm", text, flags=re.IGNORECASE)
        # Strip trailing punctuation
        text = text.strip().rstrip(".")

        # Pattern: "H[:MM] am/pm - H[:MM] am/pm"  (am/pm on both sides)
        rng_both = re.match(
            r"(\d+(?::\d+)?)\s*(am|pm)\s*[-–]\s*(\d+(?::\d+)?)\s*(am|pm)",
            text, re.IGNORECASE,
        )
        if rng_both:
            return (
                f"{rng_both.group(1)} {rng_both.group(2)}".lower(),
                f"{rng_both.group(3)} {rng_both.group(4)}".lower(),
            )

        # Pattern: "H[:MM] - H[:MM] am/pm"  (am/pm only at end)
        rng_end = re.match(
            r"(\d+(?::\d+)?)\s*[-–]\s*(\d+(?::\d+)?)\s*(am|pm)",
            text, re.IGNORECASE,
        )
        if rng_end:
            suffix = rng_end.group(3).lower()
            return (
                f"{rng_end.group(1)} {suffix}",
                f"{rng_end.group(2)} {suffix}",
            )

        # Single time
        single = re.search(r"\d+(?::\d+)?\s*(am|pm)", text, re.IGNORECASE)
        if single:
            return single.group(0).strip().lower(), None

        return None, None

    def _parse_event(self, url: str) -> dict | None:
        try:
            soup = self.fetch(url)

            # Event name — try h1, h2, h3 in order
            name_tag = soup.find("h1") or soup.find("h2") or soup.find("h3")
            event_name = name_tag.get_text(strip=True) if name_tag else None

            # Last resort: derive name from URL slug
            if not event_name:
                slug = url.rstrip("/").split("/")[-1]
                event_name = slug.replace("-", " ").title()

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

                # Time parsing — handles these formats:
                # "12-1:30 pm", "5:30 pm - 8pm", "10:30am - 12 Noon", "11:30am"
                elif re.search(r"\d+(:\d+)?\s*(am|pm|noon)", text, re.IGNORECASE):
                    start_time, end_time = self._parse_time_range(text)

            # Location: first text node after <h3>Location</h3>
            # Default to None — only set "Online" if the location text says so
            location = None
            for h3 in soup.find_all("h3"):
                if "location" in h3.get_text(strip=True).lower():
                    nxt = h3.find_next_sibling()
                    if nxt:
                        loc_text = nxt.get_text(strip=True)
                        location = loc_text if loc_text else None
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
