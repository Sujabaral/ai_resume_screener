# AI Resume Screener

AI Resume Screener is an advanced AI-powered recruitment and resume analysis system designed for real-world HR usage. The project intelligently analyzes resumes against job descriptions using semantic AI matching, NLP techniques, skill extraction, experience evaluation, and explainable scoring.

The system helps recruiters efficiently rank, analyze, and manage large volumes of candidate resumes.

---

#  Features

## Resume Parsing
- PDF resume parsing
- DOCX resume parsing
- Candidate information extraction
- Email and phone detection
- Duplicate resume detection

## AI-Powered Matching
- Semantic similarity matching using Sentence Transformers
- Job description understanding
- Dynamic skill extraction
- Responsibility matching
- Domain-aware analysis

## Smart Candidate Scoring
- Skill match scoring
- Semantic relevance scoring
- Experience scoring
- Education scoring
- Project relevance scoring
- Resume structure scoring

## Candidate Ranking
- Automatic ranking system
- Batch ranking for multiple resumes
- Explainable score breakdown
- Match percentage visualization

## Bulk Resume Upload
- Upload 50+ resumes at once
- Multi-file processing
- Fast screening pipeline

## HR Dashboard
- Recruiter/Admin login system
- Candidate management
- Job posting support
- Detailed candidate analysis view

## 📧 Email System
- Accept/Reject candidate emails
- Email logging system
- Prevent duplicate email sending
- HR-controlled communication workflow

## 📤 Export Features
- Excel export of candidate data
- Downloadable reports
- Structured HR analysis summaries

## 🛡 Security & Reliability
- Environment variable configuration
- Secure authentication
- File validation
- Database-backed candidate management

---

# 🛠 Tech Stack

## Backend
- Python
- Flask
- SQLAlchemy

## AI / ML
- Sentence Transformers
- Scikit-learn
- NLP techniques
- Semantic similarity analysis

## Resume Processing
- PyMuPDF (fitz)
- PyPDF2
- python-docx

## Database
- SQLite
- PostgreSQL ready

## Frontend
- HTML
- CSS
- Jinja2 Templates
- Chart.js

---

# 📂 Project Structure

```bash
ai_resume_screener/
│
├── app.py
├── requirements.txt
├── models.py
├── routes/
├── static/
├── templates/
├── uploads/
├── exports/
├── utils/
│   ├── smart_ranker.py
│   ├── jd_intelligence.py
│   ├── candidate_parser.py
│   ├── skill_extractor.py
│   ├── semantic_matcher.py
│   └── v4_ml_scorer.py
│
├── database/
└── README.md
```

---

# 🚀 Installation

## 1. Clone Repository

```bash
git clone https://github.com/Sujabaral/ai_resume_screener.git
```

## 2. Enter Project Folder

```bash
cd ai_resume_screener
```

## 3. Create Virtual Environment

### macOS/Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

---

## 4. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 5. Configure Environment Variables

Create a `.env` file:

```env
SECRET_KEY=your_secret_key
MAIL_USERNAME=your_email
MAIL_PASSWORD=your_password
```

---

## 6. Run the Application

```bash
python app.py
```

Open:

```bash
http://127.0.0.1:5000
```

---

# 🧠 AI Scoring Logic

The system combines multiple intelligent scoring methods:

| Component | Purpose |
|---|---|
| Semantic Matching | Understands resume meaning |
| Skill Matching | Detects required skills |
| Experience Analysis | Evaluates work experience |
| Education Analysis | Checks educational fit |
| Responsibility Matching | Matches JD responsibilities |
| Project Relevance | Evaluates candidate projects |

---

# 📸 Key Features Demonstrated

- Semantic resume understanding
- Dynamic job description parsing
- Explainable AI scoring
- Batch resume ranking
- Recruiter workflow automation
- Duplicate detection
- HR-friendly candidate analysis

---

# 📌 Future Improvements

- LLM-based resume summarization
- Interview question generation
- AI chatbot for recruiters
- Resume recommendation engine
- Real-time analytics dashboard
- Docker deployment
- Cloud deployment support
- Multi-company HR support
- REST API integration

---

# 🎯 Project Goals

This project was built to explore:

- Real-world AI applications
- NLP and semantic matching
- Recruitment automation
- Resume intelligence systems
- Flask backend development
- AI-assisted HR workflows

---

# 👨‍💻 Author

Suja Baral

GitHub:
https://github.com/Sujabaral

---

# 📄 License

This project is built for educational, learning, and portfolio purposes.
