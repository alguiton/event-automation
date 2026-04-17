import re
from datetime import datetime
from .base_scraper import BaseScraper

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


class RenewableNIScraper(BaseScraper):
    BASE_URL = "https://renewableni.com"
    EVENTS_URL = "https://renewableni.com/events/"
    ORGANISATION = "RenewableNI"

    # Path segments that are navigation, not events
    _NAV_SLUGS = {
        "events", "about", "members", "news", "contact", "join",
        "membership", "policy", "publications", "resources", "media",
    }

    def scrape(self) -> list[dict]:
        soup = self.fetch(self.EVENTS_URL)

        seen = set()
        event_links = []

        # Events are linked via <a href="/{slug}/"> near <h3> headings
        # Collect all internal page links that aren't nav/structural pages
        for a in soup.find_all("a", href=True):
            href = a["href"]
            full = href if href.startswith("http") else self.BASE_URL + href
            if not full.startswith(self.BASE_URL):
                continue
            path = full.replace(self.BASE_URL, "").strip("/")
            if not path or path in self._NAV_SLUGS or "/" in path:
                continue
            if full not in seen:
                seen.add(full)
                event_links.append(full)

        self.logger.info(f"Found {len(event_links)} RenewableNI candidate pages")
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

            for tag in soup.find_all(["p", "h2", "h3", "span", "div", "li"]):
                text = tag.get_text(strip=True)
                if not text:
                    continue

                # Date/time: "Tuesday 15 September | 9.00am – 2.30pm"
                # or "Wednesday 6 May | 10.30am - 12.30pm"
                if not start_date and any(m in text for m in MONTHS):
                    parts = [p.strip() for p in re.split(r"\|", text)]
                    for part in parts:
                        clean = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", part).strip()
                        clean = re.sub(r"^[A-Za-z]+day\s+", "", clean).strip()
                        if any(m in clean for m in MONTHS):
                            # Year may be absent — try with and without
                            for fmt in ("%d %B %Y", "%d %B", "%B %d %Y", "%B %d"):
                                try:
                                    parsed = datetime.strptime(clean[:20], fmt)
                                    if parsed.year == 1900:
                                        from datetime import date
                                        today = date.today()
                                        yr = today.year if parsed.month >= today.month else today.year + 1
                                        parsed = parsed.replace(year=yr)
                                    start_date = parsed.date().isoformat()
                                    break
                                except ValueError:
                                    continue

                    # Time in the same string "10.30am - 12.30pm" or "9.00am – 2.30pm"
                    if not start_time:
                        t_match = re.search(
                            r"(\d+[.:]\d+\s*(?:am|pm))\s*[-–]\s*(\d+[.:]\d+\s*(?:am|pm))",
                            text, re.IGNORECASE,
                        )
                        if t_match:
                            start_time = re.sub(r"\.", ":", t_match.group(1)).lower()
                            end_time = re.sub(r"\.", ":", t_match.group(2)).lower()
                        else:
                            single = re.search(r"\d+[.:]\d+\s*(am|pm)", text, re.IGNORECASE)
                            if single:
                                start_time = re.sub(r"\.", ":", single.group(0)).lower()

                # Location: standalone <p> with venue info, not a date/time line
                # Must be a direct <p> tag (not a parent container that merges org+address)
                if start_date and not location and tag.name == "p" and len(text) < 200:
                    if not re.search(r"\d+[.:]\d+\s*(am|pm)", text, re.IGNORECASE):
                        if not any(m in text for m in MONTHS):
                            if "renewableni" not in text.lower():
                                if any(kw in text.lower() for kw in [
                                    "hotel", "centre", "hall", "arena", "belfast", "online",
                                    "virtual", "street", "road", "avenue", "suite", "building",
                                    "square", "place", "house",
                                ]):
                                    location = text

            # Reject pages that look like non-events (no date found)
            if not start_date:
                return None

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
                "event_type": "Conference / Event",
                "sector_tag": "Renewable Energy",
                "link": url,
                "description": description,
            }

        except Exception as e:
            self.logger.error(f"Failed to parse RenewableNI event {url}: {e}")
            return None
