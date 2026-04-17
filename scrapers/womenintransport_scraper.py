import re
from datetime import datetime
from .base_scraper import BaseScraper

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


class WomenInTransportScraper(BaseScraper):
    BASE_URL = "https://www.womenintransport.com"
    EVENTS_URL = "https://www.womenintransport.com/events"
    ORGANISATION = "Women in Transport"

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

        self.logger.info(f"Found {len(event_links)} Women in Transport events")
        return [e for url in event_links if (e := self._parse_event(url))]

    def _parse_event(self, url: str) -> dict | None:
        try:
            soup = self.fetch(url)

            name_tag = soup.find("h1") or soup.find("h2")
            event_name = name_tag.get_text(strip=True) if name_tag else None
            if not event_name:
                event_name = url.rstrip("/").split("/")[-1].replace("-", " ").title()

            start_date = None
            start_time = None
            end_time = None
            location = None

            # Women in Transport uses <li> for date and location:
            # "Tuesday, April 21, 2026 9:00 AM" or "Friday, February 6, 2026 9:30 AM"
            # Location: "Nottingham Train Station" or "NEC NEC Birmingham" (no time)
            for li in soup.find_all("li"):
                text = li.get_text(strip=True)
                if not text:
                    continue

                # Date + time: "Tuesday, April 21, 2026 9:00 AM"
                if not start_date and any(m in text for m in MONTHS):
                    clean = re.sub(r"^[A-Za-z]+day,?\s+", "", text).strip()
                    # Try "Month Day, Year H:MM AM"
                    dt_match = re.match(
                        r"([A-Za-z]+ \d+,?\s*\d{4})\s+(\d+:\d+\s*(?:AM|PM))",
                        clean, re.IGNORECASE,
                    )
                    if dt_match:
                        date_part = dt_match.group(1).replace(",", "").strip()
                        for fmt in ("%B %d %Y", "%B %d, %Y"):
                            try:
                                start_date = datetime.strptime(date_part, fmt).date().isoformat()
                                break
                            except ValueError:
                                continue
                        if not start_time:
                            start_time = dt_match.group(2).lower()
                    else:
                        # Try plain date
                        date_only = re.match(r"([A-Za-z]+ \d+,?\s*\d{4})", clean)
                        if date_only:
                            d_str = date_only.group(1).replace(",", "").strip()
                            for fmt in ("%B %d %Y",):
                                try:
                                    start_date = datetime.strptime(d_str, fmt).date().isoformat()
                                    break
                                except ValueError:
                                    continue

                # Location: <li> without digits or time keywords
                elif not location and len(text) < 150:
                    if not re.search(r"\d{4}", text) and not re.search(r"\d+:\d+", text):
                        if not any(m in text for m in MONTHS):
                            # Filter out generic/nav words and single-word category labels
                            _skip = {"register", "book now", "read more", "events",
                                     "news", "home", "about", "contact", "join"}
                            if len(text) > 5 and text.lower() not in _skip:
                                location = text

            # Fallback: look in <p> or <div> for date
            if not start_date:
                for tag in soup.find_all(["p", "div", "span"]):
                    text = tag.get_text(strip=True)
                    if any(m in text for m in MONTHS) and re.search(r"\d{4}", text):
                        clean = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", text).strip()
                        clean = re.sub(r"^[A-Za-z]+day,?\s+", "", clean).strip()
                        for fmt in ("%B %d, %Y", "%B %d %Y", "%d %B %Y"):
                            try:
                                start_date = datetime.strptime(clean[:20], fmt).date().isoformat()
                                break
                            except ValueError:
                                continue
                        if start_date:
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
                "sector_tag": "Women in Transport",
                "link": url,
                "description": description,
            }

        except Exception as e:
            self.logger.error(f"Failed to parse Women in Transport event {url}: {e}")
            return None
