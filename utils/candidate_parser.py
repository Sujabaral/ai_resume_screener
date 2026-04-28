import re


EDUCATION_WORDS = [
    "college", "university", "school", "campus", "institute",
    "academy", "faculty", "department", "bachelor", "master",
    "engineering", "technology"
]

HEADER_BAD_WORDS = [
    "resume", "curriculum vitae", "cv", "profile", "summary",
    "objective", "email", "phone", "address", "linkedin", "github"
]


def extract_email(text):
    match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    return match.group(0) if match else "Not found"


def extract_phone(text):
    patterns = [
        r"(\+977[-\s]?)?[9][78]\d{8}",
        r"\+?\d[\d\s\-()]{8,}\d"
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0).strip()

    return "Not found"


def looks_like_person_name(line):
    clean = line.strip()

    if not clean:
        return False

    lower = clean.lower()

    if any(word in lower for word in EDUCATION_WORDS):
        return False

    if any(word in lower for word in HEADER_BAD_WORDS):
        return False

    if "@" in clean or "http" in lower or "www" in lower:
        return False

    if any(char.isdigit() for char in clean):
        return False

    words = clean.split()

    if len(words) < 2 or len(words) > 4:
        return False

    # Most names are alphabetic words with optional dots/hyphens
    for word in words:
        if not re.match(r"^[A-Za-z][A-Za-z.\-']*$", word):
            return False

    # Avoid all lowercase random lines
    if clean.islower():
        return False

    return True


def extract_name(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    # Search only top part of resume, not whole CV
    top_lines = lines[:15]

    for line in top_lines:
        if looks_like_person_name(line):
            return line

    return "Not found"


def extract_candidate_info(text):
    return {
        "name": extract_name(text),
        "email": extract_email(text),
        "phone": extract_phone(text),
    }