import re
from datetime import datetime
from .base_scraper import BaseScraper

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


class BCSWomenScraper(BaseScraper):
    BASE_URL = "https://www.bcs.org"
    # BCS Women specialist group page lists their upcoming events
    GROUP_URL = (
        "https://www.bcs.org/membership-and-registrations/member-communities/"
        "bcswomen-specialist-group/"
    )
    ORGANISATION = "BCS Women"

    def scrape(self) -> list[dict]:
        soup = self.fetch(self.GROUP_URL)

        seen = set()
        event_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            full = href if href.startswith("http") else self.BASE_URL + href
            if (
                "/events-calendar/" in full
                and full not in seen
                and "past-events" not in full
            ):
                seen.add(full)
                event_links.append(full)

        self.logger.info(f"Found {len(event_links)} BCS Women events")
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

            # BCS detail page has a "Date and time" section followed by
            # "Monday 20 April, 12:00pm - 1:00pm"
            # and a "Location" section followed by "Webinar" or address
            in_datetime = False
            in_location = False

            for tag in soup.find_all(["h2", "h3", "h4", "p", "div", "span", "li"]):
                text = tag.get_text(strip=True)
                if not text:
                    continue

                lower = text.lower()
                if "date and time" in lower or lower == "date":
                    in_datetime = True
                    in_location = False
                    continue
                if "location" in lower and len(text) < 30:
                    in_location = True
                    in_datetime = False
                    continue
                if any(h in tag.name for h in ["h2", "h3", "h4"]) and text not in ("Date and time", "Location"):
                    in_datetime = False
                    in_location = False

                # Parse date/time when in the date section
                # Format: "Monday 20 April, 12:00pm - 1:00pm"
                if in_datetime and not start_date and any(m in text for m in MONTHS + MONTH_ABBR):
                    clean = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", text).strip()
                    clean = re.sub(r"^[A-Za-z]+day\s+", "", clean).strip()

                    for fmt in ("%d %B, %Y", "%d %B %Y", "%B %d, %Y", "%d %b, %Y", "%d %b %Y"):
                        try:
                            start_date = datetime.strptime(clean[:20], fmt).date().isoformat()
                            break
                        except ValueError:
                            continue

                    # Time: "12:00pm - 1:00pm"
                    t_match = re.search(
                        r"(\d+:\d+\s*(?:am|pm))\s*[-–]\s*(\d+:\d+\s*(?:am|pm))",
                        text, re.IGNORECASE,
                    )
                    if t_match:
                        start_time = t_match.group(1).lower()
                        end_time = t_match.group(2).lower()
                    else:
                        single = re.search(r"\d+:\d+\s*(am|pm)", text, re.IGNORECASE)
                        if single:
                            start_time = single.group(0).lower()

                elif in_location and not location and len(text) < 200:
                    location = text
                    in_location = False

            # Fallback: scrape date directly from the page if in_datetime logic failed
            if not start_date:
                for tag in soup.find_all(["p", "span", "div", "time"]):
                    text = tag.get_text(strip=True)
                    if any(m in text for m in MONTHS) and re.search(r"\d{4}", text):
                        clean = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", text).strip()
                        clean = re.sub(r"^[A-Za-z]+day\s+", "", clean).strip()
                        for fmt in ("%d %B %Y", "%d %B, %Y", "%B %d, %Y"):
                            try:
                                start_date = datetime.strptime(clean[:20], fmt).date().isoformat()
                                break
                            except ValueError:
                                continue
                        if start_date:
                            break

            description = None
            synopsis_found = False
            for tag in soup.find_all(["h2", "h3", "p"]):
                if "synopsis" in tag.get_text(strip=True).lower():
                    synopsis_found = True
                    continue
                if synopsis_found and tag.name == "p":
                    text = tag.get_text(strip=True)
                    if len(text) > 40:
                        description = text[:500]
                        break

            if not description:
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
                "event_type": "Webinar / Workshop",
                "sector_tag": "Women in Technology",
                "link": url,
                "description": description,
            }

        except Exception as e:
            self.logger.error(f"Failed to parse BCS Women event {url}: {e}")
            return None
