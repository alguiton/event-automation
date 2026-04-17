import re
from datetime import datetime
from .base_scraper import BaseScraper

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


class STEMWomenScraper(BaseScraper):
    BASE_URL = "https://www.stemwomen.com"
    EVENTS_URL = "https://www.stemwomen.com/events"
    ORGANISATION = "STEM Women"

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

        self.logger.info(f"Found {len(event_links)} STEM Women events")
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

            for tag in soup.find_all(["p", "h5", "h6", "span", "div", "strong", "li"]):
                text = tag.get_text(strip=True)
                if not text:
                    continue

                # Date: "Friday 12th June 2026" or "12th June 2026"
                if not start_date and any(m in text for m in MONTHS):
                    clean = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", text).strip()
                    # Remove leading day name "Friday " etc.
                    clean = re.sub(r"^[A-Za-z]+day\s+", "", clean).strip()
                    for fmt in ("%d %B %Y", "%B %d, %Y", "%B %d %Y"):
                        try:
                            start_date = datetime.strptime(clean[:20], fmt).date().isoformat()
                            break
                        except ValueError:
                            continue

                # Time: "1:00 pm - 4:30 pm BST" or "9:00am - 5:00pm"
                # Use \d{1,2} (max 2 digits for hours) to avoid matching year digits
                if not start_time and re.search(r"(?<!\d)\d{1,2}(?::\d{2})?\s*(am|pm)", text, re.IGNORECASE):
                    clean_t = re.sub(r"\s+[A-Z]{2,4}$", "", text.strip())
                    rng = re.search(
                        r"(?<!\d)(\d{1,2}(?::\d{2})?\s*(?:am|pm))\s*[-–]\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm))",
                        clean_t, re.IGNORECASE,
                    )
                    if rng:
                        start_time = rng.group(1).lower().strip()
                        end_time = rng.group(2).lower().strip()
                    else:
                        single = re.search(r"(?<!\d)\d{1,2}(?::\d{2})?\s*(am|pm)", clean_t, re.IGNORECASE)
                        if single:
                            start_time = single.group(0).lower().strip()

            # Location: STEM Women uses <h6> for venue
            if not location:
                h6 = soup.find("h6")
                if h6:
                    text = h6.get_text(strip=True)
                    if text and len(text) < 200:
                        location = text

            # Description: skip testimonial quotes (start with " or ')
            description = None
            quote_chars = ('"', '\u201c', '\u2018', "'")
            for p in soup.find_all("p"):
                text = p.get_text(strip=True)
                if len(text) > 60 and not text.startswith(quote_chars):
                    description = text[:500]
                    break

            return {
                "event_name": event_name,
                "organisation": self.ORGANISATION,
                "start_date": start_date,
                "start_time": start_time,
                "end_time": end_time,
                "location": location,
                "event_type": "Careers Event",
                "sector_tag": "Women in STEM",
                "link": url,
                "description": description,
            }

        except Exception as e:
            self.logger.error(f"Failed to parse STEM Women event {url}: {e}")
            return None
