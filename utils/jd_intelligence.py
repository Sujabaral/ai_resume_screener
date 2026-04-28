import re
from collections import Counter


SKILL_SEPARATORS = r"[,;/\n|]+"


STOPWORDS = {
    "and", "or", "the", "a", "an", "to", "of", "for", "with", "in", "on",
    "by", "as", "such", "role", "candidate", "ability"
}


# --------------------------------------------------
# CLEANING
# --------------------------------------------------

def clean_skill(skill):
    skill = skill.strip().lower()
    skill = re.sub(r"[().]", "", skill)
    skill = re.sub(r"\s+", " ", skill)
    return skill


def split_skills(text):
    if not text:
        return []

    parts = re.split(SKILL_SEPARATORS, text)
    skills = []

    for part in parts:
        skill = clean_skill(part)

        skill = re.sub(
            r"^(such as|including|like|using|experience with|knowledge of|familiar with)\s+",
            "",
            skill
        )

        if 2 <= len(skill) <= 40 and skill not in STOPWORDS:
            skills.append(skill)

    return list(set(skills))


# --------------------------------------------------
# SMART SKILL EXTRACTION
# --------------------------------------------------

def extract_strong_skill_patterns(text):
    patterns = [
        r"(?:must have|required|requirements|skills)[:\-]\s*(.+)",
        r"(?:experience with|proficient in|strong in|hands-on experience in)\s+(.+)",
        r"(?:tools|technologies|frameworks)\s+(?:such as|like)\s+(.+)"
    ]

    skills = set()

    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)

        for match in matches:
            match = re.split(r"\.|\n", match)[0]
            skills.update(split_skills(match))

    return skills


def extract_capitalized_tools(text):
    candidates = re.findall(
        r"\b(?:[A-Z][a-zA-Z0-9+#.-]*(?:\s+[A-Z][a-zA-Z0-9+#.-]*){0,2})\b",
        text or ""
    )

    tools = set()

    for item in candidates:
        cleaned = clean_skill(item)

        if 2 <= len(cleaned) <= 40:
            # must look like real tool (not random word)
            if any(c.isupper() for c in item[1:]) or len(item.split()) >= 2:
                tools.add(cleaned)

    return tools


def extract_contextual_skills(text):
    """
    Extracts frequent meaningful terms (filters noise)
    """
    words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9+#.-]{2,}\b", text.lower())

    words = [w for w in words if w not in STOPWORDS]

    counter = Counter(words)

    # Keep only meaningful frequency words
    return {
        word for word, freq in counter.items()
        if freq >= 2 and len(word) > 3
    }


# --------------------------------------------------
# EXPERIENCE
# --------------------------------------------------

def extract_years_required(text, manual_years=0):
    text = (text or "").lower()

    patterns = [
        r"(\d+)\+?\s*(?:years|yrs)\s+(?:of\s+)?experience",
        r"minimum\s+(\d+)",
        r"at least\s+(\d+)",
        r"(\d+)\+?\s*years"
    ]

    years = []

    for pattern in patterns:
        years.extend([int(x) for x in re.findall(pattern, text)])

    return max(years) if years else int(manual_years or 0)


# --------------------------------------------------
# RESPONSIBILITIES
# --------------------------------------------------

def extract_responsibilities(text):
    lines = [line.strip("•-* ").strip() for line in text.splitlines() if line.strip()]

    action_words = [
        "develop", "design", "build", "create", "implement",
        "manage", "analyze", "test", "deploy", "maintain"
    ]

    responsibilities = []

    for line in lines:
        if any(word in line.lower() for word in action_words):
            responsibilities.append(line)

    return responsibilities[:15]


# --------------------------------------------------
# REQUIRED VS PREFERRED (IMPROVED)
# --------------------------------------------------

def separate_required_preferred(skills, text):
    text_lower = text.lower()

    required = set()
    preferred = set()

    for skill in skills:
        window = 100

        pattern_required = rf"(must|required)[^.]{0,{window}}{re.escape(skill)}"
        pattern_preferred = rf"(preferred|nice to have|plus)[^.]{0,{window}}{re.escape(skill)}"

        if re.search(pattern_preferred, text_lower):
            preferred.add(skill)
        elif re.search(pattern_required, text_lower):
            required.add(skill)
        else:
            # fallback: treat as required but softer
            required.add(skill)

    return required, preferred


# --------------------------------------------------
# DOMAIN DETECTION (IMPROVED)
# --------------------------------------------------

def detect_domain(text, skills):
    combined = (text + " " + " ".join(skills)).lower()

    domain_map = {
        "AI / Machine Learning": ["machine learning", "deep learning", "nlp", "tensorflow"],
        "Software Engineering": ["api", "backend", "frontend", "database"],
        "Data / Analytics": ["data", "analytics", "sql", "dashboard"],
        "Cloud / DevOps": ["aws", "docker", "kubernetes"],
        "Cybersecurity": ["security", "vulnerability", "threat"],
        "Design / UI UX": ["figma", "ui", "ux"],
        "Marketing / Content": ["seo", "marketing", "content"],
    }

    scores = {}

    for domain, keywords in domain_map.items():
        scores[domain] = sum(k in combined for k in keywords)

    best = max(scores, key=scores.get)

    return best if scores[best] > 0 else "General"


# --------------------------------------------------
# MAIN FUNCTION
# --------------------------------------------------

def extract_dynamic_jd_requirements(
    job_description,
    manual_required="",
    manual_preferred="",
    manual_years=0,
    manual_qualification=""
):
    jd = job_description or ""

    skills = set()

    # STRONG extraction first
    skills.update(extract_strong_skill_patterns(jd))

    # tools (React, AWS, etc)
    skills.update(extract_capitalized_tools(jd))

    # contextual (only meaningful frequent words)
    skills.update(extract_contextual_skills(jd))

    # manual override
    skills.update(split_skills(manual_required))

    # FILTER FINAL SKILLS (IMPORTANT)
    skills = {
        s for s in skills
        if 2 <= len(s) <= 30 and not s.isdigit()
    }

    required, preferred = separate_required_preferred(skills, jd)

    responsibilities = extract_responsibilities(jd)
    years = extract_years_required(jd, manual_years)
    domain = detect_domain(jd, skills)

    return {
        "clean_jd": jd,
        "job_description": jd,

        "domain": domain,

        "required_skills": sorted(required),
        "preferred_skills": sorted(preferred),

        "responsibilities": responsibilities,

        "required_years": years,
        "manual_years": years,

        "qualification": manual_qualification or "",
    }