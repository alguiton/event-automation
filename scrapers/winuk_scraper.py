import re
from datetime import date, datetime
from .base_scraper import BaseScraper

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}
MONTH_NAMES = list(MONTHS.keys())


def _infer_year(month_num: int, day: int) -> int:
    today = date.today()
    try:
        d = date(today.year, month_num, day)
        return today.year if d >= today else today.year + 1
    except ValueError:
        return today.year


class WiNUKScraper(BaseScraper):
    BASE_URL = "https://www.winuk.org.uk"
    EVENTS_URL = "https://www.winuk.org.uk/events/"
    ORGANISATION = "Women in Nuclear UK"

    def scrape(self) -> list[dict]:
        soup = self.fetch(self.EVENTS_URL)

        seen = set()
        event_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            full = href if href.startswith("http") else self.BASE_URL + href
            if (
                "/event/" in full
                and full.rstrip("/") != self.EVENTS_URL.rstrip("/")
                and full not in seen
            ):
                seen.add(full)
                event_links.append(full)

        self.logger.info(f"Found {len(event_links)} WiN UK events")
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

            for tag in soup.find_all(["div", "span", "p", "li", "strong", "h4", "time"]):
                text = tag.get_text(strip=True)
                if not text:
                    continue

                # Date: "April 21" or "April 21, 2026" or "21 April 2026"
                if not start_date:
                    for m_name, m_num in MONTHS.items():
                        if m_name in text.lower():
                            clean = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", text).strip()
                            # With year
                            for fmt in ("%B %d, %Y", "%B %d %Y", "%d %B %Y"):
                                try:
                                    start_date = datetime.strptime(clean[:20], fmt).date().isoformat()
                                    break
                                except ValueError:
                                    continue
                            # Without year: "April 21"
                            if not start_date:
                                m = re.search(rf"\b({m_name})\s+(\d{{1,2}})\b", text, re.IGNORECASE)
                                if m:
                                    day = int(m.group(2))
                                    yr = _infer_year(m_num, day)
                                    try:
                                        start_date = date(yr, m_num, day).isoformat()
                                    except ValueError:
                                        pass
                            break

                # Time: "1:00 pm - 2:00 pm" or "4:30 pm - 6:00 pm"
                if not start_time and re.search(r"\d+:\d+\s*(am|pm)", text, re.IGNORECASE):
                    rng = re.match(
                        r"(\d+:\d+\s*(?:am|pm))\s*[-–]\s*(\d+:\d+\s*(?:am|pm))",
                        text, re.IGNORECASE,
                    )
                    if rng:
                        start_time = rng.group(1).lower().strip()
                        end_time = rng.group(2).lower().strip()
                    else:
                        single = re.search(r"\d+:\d+\s*(am|pm)", text, re.IGNORECASE)
                        if single:
                            start_time = single.group(0).lower().strip()

                # Location
                if not location and len(text) < 150:
                    lower = text.lower()
                    if any(kw in lower for kw in ["online", "virtual", "zoom", "teams", "webinar"]):
                        location = "Online"

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
                "event_type": "Workshop / Event",
                "sector_tag": "Women in Nuclear",
                "link": url,
                "description": description,
            }

        except Exception as e:
            self.logger.error(f"Failed to parse WiN UK event {url}: {e}")
            return None
