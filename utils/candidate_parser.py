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

SECTION_HEADINGS = {
    "summary": ["summary", "profile", "objective", "professional summary"],
    "skills": ["skills", "technical skills", "core skills", "key skills"],
    "experience": ["experience", "work experience", "professional experience", "employment history"],
    "education": ["education", "academic background", "qualification"],
    "projects": ["projects", "academic projects", "personal projects"],
    "certifications": ["certifications", "certificate", "training"],
}


def clean_text(text):
    text = text or ""
    text = re.sub(r"\r", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_email(text):
    match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text or "")
    return match.group(0) if match else "Not found"


def extract_phone(text):
    patterns = [
        r"(\+977[-\s]?)?[9][78]\d{8}",
        r"\+?\d[\d\s\-()]{8,}\d"
    ]

    for pattern in patterns:
        match = re.search(pattern, text or "")
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

    for word in words:
        if not re.match(r"^[A-Za-z][A-Za-z.\-']*$", word):
            return False

    if clean.islower():
        return False

    return True


def extract_name(text):
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    top_lines = lines[:15]

    for line in top_lines:
        if looks_like_person_name(line):
            return line

    return "Not found"


def normalize_heading(line):
    line = line.strip().lower()
    line = re.sub(r"[:\-]", "", line)
    line = re.sub(r"\s+", " ", line)
    return line


def detect_section_heading(line):
    normalized = normalize_heading(line)

    for section, headings in SECTION_HEADINGS.items():
        if normalized in headings:
            return section

    return None


def extract_sections(text):
    text = clean_text(text)
    sections = {
        "summary": "",
        "skills": "",
        "experience": "",
        "education": "",
        "projects": "",
        "certifications": "",
        "general": "",
    }

    current = "general"

    for line in text.splitlines():
        stripped = line.strip()

        if not stripped:
            continue

        section = detect_section_heading(stripped)

        if section:
            current = section
            continue

        sections[current] += stripped + "\n"

    return {key: value.strip() for key, value in sections.items()}


def extract_candidate_info(text):
    text = clean_text(text)
    sections = extract_sections(text)

    return {
        "name": extract_name(text),
        "email": extract_email(text),
        "phone": extract_phone(text),

        "summary_text": sections.get("summary", ""),
        "skills_text": sections.get("skills", ""),
        "experience_text": sections.get("experience", ""),
        "education_text": sections.get("education", ""),
        "projects_text": sections.get("projects", ""),
        "certifications_text": sections.get("certifications", ""),
        "general_text": sections.get("general", ""),
    }