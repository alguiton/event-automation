import re
from datetime import datetime
from .base_scraper import BaseScraper

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


class WomenInRailScraper(BaseScraper):
    BASE_URL = "https://womeninrail.org"
    EVENTS_URL = "https://womeninrail.org/events/"
    ORGANISATION = "Women in Rail"

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

        self.logger.info(f"Found {len(event_links)} Women in Rail events")
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

            # Women in Rail uses <strong> for date, time, and location
            # Date: "Thu, 2nd Jul 2026"  Time: "17:30 - 21:00"  Location: address string
            for strong in soup.find_all("strong"):
                text = strong.get_text(strip=True)
                if not text:
                    continue

                # Date: contains a month name
                if not start_date and any(m in text for m in MONTHS):
                    clean = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", text).strip()
                    # Remove "Thu, " or "Monday, " prefix
                    clean = re.sub(r"^[A-Za-z]+,?\s+", "", clean).strip()
                    for fmt in ("%d %b %Y", "%d %B %Y", "%B %d, %Y"):
                        try:
                            start_date = datetime.strptime(clean[:20], fmt).date().isoformat()
                            break
                        except ValueError:
                            continue

                # Time: "17:30 - 21:00" or "10:00am - 4:00pm"
                elif not start_time and re.search(r"\d+:\d+", text):
                    # 24h format
                    t24 = re.match(r"(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})$", text.strip())
                    if t24:
                        start_time = t24.group(1)
                        end_time = t24.group(2)
                    else:
                        # am/pm format
                        t_ampm = re.match(
                            r"(\d+:\d+\s*(?:am|pm))\s*[-–]\s*(\d+:\d+\s*(?:am|pm))",
                            text, re.IGNORECASE,
                        )
                        if t_ampm:
                            start_time = t_ampm.group(1).lower()
                            end_time = t_ampm.group(2).lower()
                        elif re.search(r"\d+:\d+", text):
                            start_time = re.search(r"\d+:\d+", text).group(0)

                # Location: everything else that isn't a date or time
                elif not location and len(text) < 200:
                    if not any(m in text for m in MONTHS) and not re.search(r"^\d+:\d+", text):
                        location = text

            # Fallback: look in h3/p for date if <strong> didn't yield one
            if not start_date:
                for tag in soup.find_all(["h3", "p"]):
                    text = tag.get_text(strip=True)
                    if any(m in text for m in MONTHS):
                        clean = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", text)
                        clean = re.sub(r"^[A-Za-z]+,?\s+", "", clean).strip()
                        # Bullet-point format "02 • 07 • 2026"
                        bullet = re.match(r"(\d{1,2})\s*[•·]\s*(\d{1,2})\s*[•·]\s*(\d{4})", text)
                        if bullet:
                            try:
                                start_date = datetime(
                                    int(bullet.group(3)),
                                    int(bullet.group(2)),
                                    int(bullet.group(1)),
                                ).date().isoformat()
                                break
                            except ValueError:
                                pass
                        for fmt in ("%d %B %Y", "%d %b %Y"):
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
                "sector_tag": "Women in Rail",
                "link": url,
                "description": description,
            }

        except Exception as e:
            self.logger.error(f"Failed to parse Women in Rail event {url}: {e}")
            return None
