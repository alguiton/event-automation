import re
from datetime import date, datetime
from .base_scraper import BaseScraper

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}


def _infer_year(month_num: int, day: int) -> int:
    today = date.today()
    try:
        d = date(today.year, month_num, day)
        return today.year if d >= today else today.year + 1
    except ValueError:
        return today.year


class WomenInSustainabilityScraper(BaseScraper):
    BASE_URL = "https://womeninsustainability.net"
    EVENTS_URL = "https://womeninsustainability.net/events/"
    ORGANISATION = "Women in Sustainability"

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

        self.logger.info(f"Found {len(event_links)} Women in Sustainability events")
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

            # WordPress format: "April 16 @ 1:00 pm – 1:45 pm BST"
            # Appears in the page title or a <abbr>/<span> near the top
            for tag in soup.find_all(["h1", "h2", "h3", "abbr", "span", "div", "p", "time"]):
                text = tag.get_text(strip=True)
                if not text:
                    continue

                # Date + time in WordPress format "Month DD @ H:MM am – H:MM am"
                wp_match = re.match(
                    r"([A-Za-z]+)\s+(\d{1,2})(?:,\s*(\d{4}))?\s*@\s*"
                    r"(\d+:\d+\s*(?:am|pm))\s*[-–]\s*(\d+:\d+\s*(?:am|pm))",
                    text, re.IGNORECASE,
                )
                if wp_match:
                    m_name = wp_match.group(1).lower()
                    m_num = MONTHS.get(m_name)
                    day = int(wp_match.group(2))
                    yr = int(wp_match.group(3)) if wp_match.group(3) else _infer_year(m_num, day)
                    if m_num:
                        try:
                            start_date = date(yr, m_num, day).isoformat()
                        except ValueError:
                            pass
                    # Strip timezone from times
                    start_time = re.sub(r"\s+[A-Z]{2,4}$", "", wp_match.group(4)).lower().strip()
                    end_time = re.sub(r"\s+[A-Z]{2,4}$", "", wp_match.group(5)).lower().strip()
                    break

                # Fallback date only
                if not start_date:
                    for m_name, m_num in MONTHS.items():
                        if m_name in text.lower():
                            m = re.search(
                                rf"\b({m_name})\s+(\d{{1,2}}),?\s*(\d{{4}})?",
                                text, re.IGNORECASE,
                            )
                            if m:
                                day = int(m.group(2))
                                yr = int(m.group(3)) if m.group(3) else _infer_year(m_num, day)
                                try:
                                    start_date = date(yr, m_num, day).isoformat()
                                except ValueError:
                                    pass
                            break

            # Location
            for tag in soup.find_all(["p", "div", "span"]):
                text = tag.get_text(strip=True)
                if not text or len(text) > 200:
                    continue
                lower = text.lower()
                if any(kw in lower for kw in ["online", "virtual", "zoom", "teams", "webinar"]):
                    location = "Online"
                    break
                if any(kw in lower for kw in ["venue", "location", "street", "road", "centre"]):
                    location = text
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
                "event_type": "Workshop / Webinar",
                "sector_tag": "Women in Sustainability",
                "link": url,
                "description": description,
            }

        except Exception as e:
            self.logger.error(f"Failed to parse Women in Sustainability event {url}: {e}")
            return None
