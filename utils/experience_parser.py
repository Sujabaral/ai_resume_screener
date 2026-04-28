import re
from datetime import datetime

MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


def clean_text(text):
    text = text.lower()
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_date(text):
    text = text.lower().replace(".", "").strip()

    if text in ["present", "current", "now", "ongoing", "till date"]:
        return datetime.now()

    # Jan 2021 / January 2021
    match = re.search(r"([a-z]+)\s+(\d{4})", text)
    if match:
        month = MONTHS.get(match.group(1)[:3], 1)
        year = int(match.group(2))
        return datetime(year, month, 1)

    # 2021
    match = re.search(r"\b(20\d{2}|19\d{2})\b", text)
    if match:
        return datetime(int(match.group(1)), 1, 1)

    return None


def years_between(start, end):
    if not start or not end:
        return 0

    if end < start:
        return 0

    months = (end.year - start.year) * 12 + (end.month - start.month)
    return round(months / 12, 1)


def extract_explicit_years(text):
    text = clean_text(text)

    patterns = [
        r"(\d+(?:\.\d+)?)\+?\s*(?:years|year|yrs|yr)\s+(?:of\s+)?(?:professional\s+)?experience",
        r"(?:experience|exp)\s*(?:of|:|-)?\s*(\d+(?:\.\d+)?)\+?\s*(?:years|year|yrs|yr)",
        r"over\s+(\d+(?:\.\d+)?)\s*(?:years|year|yrs|yr)",
        r"more than\s+(\d+(?:\.\d+)?)\s*(?:years|year|yrs|yr)",
        r"(\d+(?:\.\d+)?)\+?\s*(?:years|year|yrs|yr)\s+in\s+[a-z0-9+#.\s]+",
    ]

    years = []

    for pattern in patterns:
        for match in re.findall(pattern, text):
            try:
                years.append(float(match))
            except Exception:
                pass

    return max(years) if years else 0


def extract_date_range_years(text):
    text = clean_text(text)

    date_part = r"(?:jan|january|feb|february|mar|march|apr|april|may|jun|june|jul|july|aug|august|sep|sept|september|oct|october|nov|november|dec|december)?\.?\s*(?:19\d{2}|20\d{2}|present|current|now|ongoing|till date)"

    pattern = re.compile(
        rf"({date_part})\s*(?:-|to)\s*({date_part})",
        re.IGNORECASE
    )

    ranges = []

    for match in pattern.finditer(text):
        start = parse_date(match.group(1))
        end = parse_date(match.group(2))

        years = years_between(start, end)

        if 0 < years <= 40:
            ranges.append(years)

    # Prevent unrealistic double-counting from messy resumes
    total = sum(ranges)

    return round(min(total, 40), 1)


def extract_candidate_years(text):
    explicit_years = extract_explicit_years(text)
    date_range_years = extract_date_range_years(text)

    return round(max(explicit_years, date_range_years), 1)