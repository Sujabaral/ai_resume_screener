from email.mime import message
import os
from dotenv import load_dotenv
from sqlalchemy import or_
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from flask import render_template
from flask_login import login_required
from models import Job, Candidate, EmailLog
from models import db, User, Job, Candidate, EmailLog
import hashlib
from utils.file_parser import allowed_file, extract_text_from_file
from utils.candidate_parser import extract_candidate_info
from utils.jd_intelligence import extract_dynamic_jd_requirements
from utils.smart_ranker import rank_candidate
from utils.excel_exporter import export_to_excel
from utils.email_sender import send_email, acceptance_template, rejection_template
from flask import send_from_directory

basedir = os.path.abspath(os.path.dirname(__file__))

load_dotenv()

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-this")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{os.path.join(basedir, 'midas_hr.db')}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["UPLOAD_FOLDER"] = "uploads"
app.config["EXPORT_FOLDER"] = "exports"
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100MB max upload request

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["EXPORT_FOLDER"], exist_ok=True)

db.init_app(app)

with app.app_context():
    db.create_all()

    admin = User.query.filter_by(email="admin@midas.local").first()
    if not admin:
        admin = User(
            name="MIDAS Admin",
            email="admin@midas.local",
            role="admin"
        )
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.route("/init-db")
def init_db():
    db.create_all()

    admin = User.query.filter_by(email="admin@midas.local").first()

    if not admin:
        admin = User(
            name="MIDAS Admin",
            email="admin@midas.local",
            role="admin"
        )
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()

    return "Database initialized. Login: admin@midas.local / admin123"


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("index"))

        flash("Invalid email or password.")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/uploads/<path:filename>")
@login_required
def preview_resume(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        job_title = request.form.get("job_title", "").strip()
        manual_years = int(request.form.get("required_years", 0))
        manual_qualification = request.form.get("qualification", "").strip()
        manual_required = request.form.get("required_skills", "")
        manual_preferred = request.form.get("preferred_skills", "")
        job_description = request.form.get("job_description", "").strip()

        files = request.files.getlist("resumes")

        if not files or files[0].filename == "":
            flash("Please upload at least one resume.")
            return redirect(url_for("index"))

        jd_data = extract_dynamic_jd_requirements(
            job_description=job_description,
            manual_required=manual_required,
            manual_preferred=manual_preferred,
            manual_years=manual_years,
            manual_qualification=manual_qualification,
        )

        job = Job(
            title=job_title,
            required_years=jd_data["required_years"],
            qualification=manual_qualification,
            required_skills=", ".join(jd_data["required_skills"]),
            preferred_skills=", ".join(jd_data["preferred_skills"]),
            job_description=job_description,
            created_by=current_user.id,
        )

        db.session.add(job)
        db.session.commit()

        processed_count = 0
        skipped_count = 0

        for file in files:
            if not file or file.filename == "":
                skipped_count += 1
                continue

            if not allowed_file(file.filename):
                skipped_count += 1
                continue

            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
            saved_filename = f"{timestamp}_{filename}"
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], saved_filename)

            file.save(file_path)

            cv_text = extract_text_from_file(file_path)

            if not cv_text:
                skipped_count += 1
                continue

            candidate_info = extract_candidate_info(cv_text)
            rank = rank_candidate(cv_text, jd_data)

            skill_data = rank.get("skill_data", {})

            candidate = Candidate(
                job_id=job.id,
                file_name=saved_filename,

                name=candidate_info.get("name", "Not found"),
                email=candidate_info.get("email", "Not found"),
                phone=candidate_info.get("phone", "Not found"),

                resume_text=cv_text,

                overall_score=rank.get("overall_score", 0),
                review_label=rank.get("label", "Manual Review"),

                required_years=rank.get("required_years", jd_data["required_years"]),
                candidate_years=rank.get("candidate_years", 0),

                required_skill_score=skill_data.get("required_score", 0),
                preferred_skill_score=skill_data.get("preferred_score", 0),
                semantic_score=rank.get("semantic_score", 0),
                responsibility_score=rank.get("responsibility_score", 0),
                experience_score=rank.get("experience_score", 0),
                education_score=rank.get("education_score", 0),
                project_score=rank.get("project_score", 0),
                structure_score=rank.get("structure_score", 0),
                penalty=rank.get("penalty", 0),

                skills_required=", ".join(jd_data.get("required_skills", [])) or "None",
                skills_present=", ".join(skill_data.get("matched_required", [])) or "None",
                skills_missing=", ".join(skill_data.get("missing_required", [])) or "None",
                preferred_skills_present=", ".join(skill_data.get("matched_preferred", [])) or "None",

                detected_sections=", ".join(rank.get("sections", [])) or "Not clear",
                education_analysis=rank.get("education_note", "Not analyzed"),
                ai_analysis=rank.get("analysis", "No analysis available"),

                hr_decision="Pending Manual Review",
                email_sent=False,
                email_locked=False,
            )

            db.session.add(candidate)
            processed_count += 1

        db.session.commit()

        flash(f"Processed {processed_count} resumes. Skipped {skipped_count} files.")

        return redirect(url_for("ranking", job_id=job.id))

    return render_template("index.html")


@app.route("/jobs")
@login_required
def jobs():
    all_jobs = Job.query.order_by(Job.created_at.desc()).all()
    return render_template("jobs.html", jobs=all_jobs)

def generate_resume_hash(text):
    cleaned = " ".join(text.lower().split())
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()

@app.route("/ranking/<int:job_id>")
@login_required
def ranking(job_id):
    job = Job.query.get_or_404(job_id)

    candidates = Candidate.query.filter_by(job_id=job.id).order_by(
        Candidate.overall_score.desc()
    ).all()

    total_candidates = len(candidates)

    for index, c in enumerate(candidates, start=1):
        c.rank = index

        if c.ai_analysis:
            c.ai_analysis = c.ai_analysis.replace(
                "#N/A",
                f"#{index} out of {total_candidates}"
            )

    db.session.commit()

    return render_template(
        "ranking.html",
        job=job,
        candidates=candidates,
        bias_warning=True
    )

@app.route("/job/<int:job_id>/download-excel")
@login_required
def download_excel(job_id):
    job = Job.query.get_or_404(job_id)

    candidates = Candidate.query.filter_by(job_id=job.id).order_by(
        Candidate.overall_score.desc()
    ).all()

    rows = []

    for index, c in enumerate(candidates, start=1):
        rows.append({
            "Rank": index,
            "Candidate Name": c.name,
            "Email": c.email,
            "Phone": c.phone,
            "Overall Score": c.overall_score,
            "Review Label": c.review_label,
            "Required Years": c.required_years,
            "Candidate Years": c.candidate_years,
            "Required Skill Score": c.required_skill_score,
            "Preferred Skill Score": c.preferred_skill_score,
            "Semantic BERT Score": c.semantic_score,
            "Responsibility Score": c.responsibility_score,
            "Experience Score": c.experience_score,
            "Education Score": c.education_score,
            "Project Score": c.project_score,
            "CV Structure Score": c.structure_score,
            "Penalty": c.penalty,
            "Skills Required": c.skills_required,
            "Skills Present": c.skills_present,
            "Skills Missing": c.skills_missing,
            "Preferred Skills Present": c.preferred_skills_present,
            "Detected Sections": c.detected_sections,
            "Education Analysis": c.education_analysis,
            "AI Analysis": c.ai_analysis,
            "HR Decision": c.hr_decision,
            "Email Sent": "Yes" if c.email_sent else "No",
            "Email Locked": "Yes" if c.email_locked else "No",
            "Email Sent At": c.email_sent_at,
        })

    excel_path = export_to_excel(rows, app.config["EXPORT_FOLDER"])
    return send_file(excel_path, as_attachment=True)
@app.route("/send-email/<int:candidate_id>", methods=["POST"])
@login_required
def send_candidate_email(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)
    job = Job.query.get_or_404(candidate.job_id)

    if candidate.email_locked or candidate.email_sent:
        flash("Email already sent to this candidate. This candidate is locked.", "warning")
        return redirect(url_for("ranking", job_id=job.id))

    if not candidate.email or candidate.email.lower().strip() in ["not found", "none", ""]:
        flash("Candidate email not found. Please edit candidate email before sending.", "danger")
        return redirect(url_for("candidate_detail", candidate_id=candidate.id))

    email_type = request.form.get("email_type")

    if email_type == "accepted":
        subject = f"Congratulations - Application Update for {job.title}"
        body = acceptance_template(candidate.name or "Candidate", job.title)
        decision = "Accepted"

    elif email_type == "rejected":
        subject = f"Application Update for {job.title}"
        body = rejection_template(candidate.name or "Candidate", job.title)
        decision = "Rejected"

    else:
        flash("Invalid email option selected.", "danger")
        return redirect(url_for("ranking", job_id=job.id))

    success, message = send_email(candidate.email.strip().lower(), subject, body)

    log = EmailLog(
        candidate_id=candidate.id,
        job_id=job.id,
        recipient_email=candidate.email.strip().lower(),
        email_type=email_type,
        subject=subject,
        sent_by=current_user.id,
        status="sent" if success else "failed",
        message=message
    )

    db.session.add(log)

    if success:
        normalized_email = candidate.email.strip().lower()

        duplicate_candidates = Candidate.query.filter(
            db.func.lower(db.func.trim(Candidate.email)) == normalized_email,
            Candidate.job_id == job.id
        ).all()

        for dup in duplicate_candidates:
            dup.email_sent = True
            dup.email_locked = True
            dup.email_sent_at = datetime.utcnow()
            dup.email_sent_by = current_user.id
            dup.hr_decision = decision

        flash(
            f"{decision} email sent successfully to {candidate.email}. "
            f"{len(duplicate_candidates)} duplicate record(s) marked as sent.",
            "success"
        )

    else:
        flash(f"Email failed: {message}", "danger")

    db.session.commit()
    return redirect(url_for("ranking", job_id=job.id))


@app.route("/candidate/<int:candidate_id>")
@login_required
def candidate_detail(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)
    job = Job.query.get_or_404(candidate.job_id)

    def level(score):
        score = float(score or 0)
        if score < 50:
            return "low"
        elif score < 75:
            return "mid"
        return "high"

    def label(score, word="Match"):
        score = float(score or 0)
        if score < 50:
            return f"Low {word}"
        elif score < 75:
            return f"Average {word}"
        return f"Strong {word}"

    candidate.overall_level = level(candidate.overall_score)
    candidate.semantic_level = level(candidate.semantic_score)
    candidate.responsibility_level = level(candidate.responsibility_score)
    candidate.experience_level = level(candidate.experience_score)

    candidate.overall_label = label(candidate.overall_score, "Match")
    candidate.semantic_label = label(candidate.semantic_score, "Match")
    candidate.responsibility_label = label(candidate.responsibility_score, "Fit")
    candidate.experience_label = label(candidate.experience_score, "Match")

    if candidate.overall_score >= 80:
        candidate.recommendation = "Recommended for Interview"
    elif candidate.overall_score >= 60:
        candidate.recommendation = "Consider for Interview"
    else:
        candidate.recommendation = "Needs Manual Review"

    if candidate.overall_score >= 80 and candidate.semantic_score >= 70:
        candidate.confidence = "High"
    elif candidate.overall_score >= 60:
        candidate.confidence = "Medium"
    else:
        candidate.confidence = "Low"

    score_breakdown = [
        {
            "label": "Overall Match",
            "value": round(candidate.overall_score or 0, 2),
            "level": level(candidate.overall_score),
        },
        {
            "label": "Semantic Match",
            "value": round(candidate.semantic_score or 0, 2),
            "level": level(candidate.semantic_score),
        },
        {
            "label": "Responsibility Fit",
            "value": round(candidate.responsibility_score or 0, 2),
            "level": level(candidate.responsibility_score),
        },
        {
            "label": "Experience Match",
            "value": round(candidate.experience_score or 0, 2),
            "level": level(candidate.experience_score),
        },
        {
            "label": "Education Match",
            "value": round(candidate.education_score or 0, 2),
            "level": level(candidate.education_score),
        },
        {
            "label": "Project Relevance",
            "value": round(candidate.project_score or 0, 2),
            "level": level(candidate.project_score),
        },
        {
            "label": "Structure Score",
            "value": round(candidate.structure_score or 0, 2),
            "level": level(candidate.structure_score),
        },
    ]

    required_skills = []
    preferred_skills = []

    if job.required_skills:
        required_skills = [s.strip() for s in job.required_skills.split(",") if s.strip()]

    if job.preferred_skills:
        preferred_skills = [s.strip() for s in job.preferred_skills.split(",") if s.strip()]

    return render_template(
        "candidate_detail.html",
        candidate=candidate,
        job=job,
        score_breakdown=score_breakdown,
        required_skills=required_skills,
        preferred_skills=preferred_skills,
    )    

@app.route("/audit/email-logs")
@login_required
def email_logs():
    logs = EmailLog.query.order_by(EmailLog.sent_at.desc()).all()
    return render_template("email_logs.html", logs=logs)

@app.route("/admin")
@login_required
def admin_dashboard():
    total_jobs = Job.query.count()
    total_candidates = Candidate.query.count()

    high_matches = Candidate.query.filter(Candidate.overall_score >= 75).count()
    medium_matches = Candidate.query.filter(
        Candidate.overall_score >= 50,
        Candidate.overall_score < 75
    ).count()
    low_matches = Candidate.query.filter(Candidate.overall_score < 50).count()

    emails_sent = Candidate.query.filter_by(email_sent=True).count()
    pending_emails = Candidate.query.filter_by(email_sent=False).count()

    avg_score_result = db.session.query(db.func.avg(Candidate.overall_score)).scalar()
    avg_score = round(avg_score_result or 0, 2)

    recent_jobs = Job.query.order_by(Job.created_at.desc()).limit(5).all()
    recent_candidates = Candidate.query.order_by(Candidate.created_at.desc()).limit(10).all()

    return render_template(
        "admin.html",
        total_jobs=total_jobs,
        total_candidates=total_candidates,
        high_matches=high_matches,
        medium_matches=medium_matches,
        low_matches=low_matches,
        emails_sent=emails_sent,
        pending_emails=pending_emails,
        avg_score=avg_score,
        recent_jobs=recent_jobs,
        recent_candidates=recent_candidates,
    )
    
if __name__ == "__main__":
    app.run(debug=True, port=5050)