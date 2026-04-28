from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    role = db.Column(db.String(20), default="hr")  # hr or admin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(200), nullable=False)
    required_years = db.Column(db.Integer, default=0)
    qualification = db.Column(db.String(255))
    required_skills = db.Column(db.Text)
    preferred_skills = db.Column(db.Text)
    job_description = db.Column(db.Text)

    created_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    candidates = db.relationship("Candidate", backref="job", lazy=True)


class Candidate(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    job_id = db.Column(db.Integer, db.ForeignKey("job.id"), nullable=False)

    file_name = db.Column(db.String(255))
    name = db.Column(db.String(160), default="Not found")
    email = db.Column(db.String(160), default="Not found")
    phone = db.Column(db.String(80), default="Not found")

    resume_text = db.Column(db.Text)

    overall_score = db.Column(db.Float, default=0)
    review_label = db.Column(db.String(80), default="Manual Review")

    required_years = db.Column(db.Float, default=0)
    candidate_years = db.Column(db.Float, default=0)

    required_skill_score = db.Column(db.Float, default=0)
    preferred_skill_score = db.Column(db.Float, default=0)
    semantic_score = db.Column(db.Float, default=0)
    responsibility_score = db.Column(db.Float, default=0)
    experience_score = db.Column(db.Float, default=0)
    education_score = db.Column(db.Float, default=0)
    project_score = db.Column(db.Float, default=0)
    structure_score = db.Column(db.Float, default=0)
    penalty = db.Column(db.Float, default=0)
    resume_hash = db.Column(db.String(64))
    skills_required = db.Column(db.Text)
    skills_present = db.Column(db.Text)
    skills_missing = db.Column(db.Text)
    preferred_skills_present = db.Column(db.Text)
    rank = db.Column(db.Integer, nullable=True)
    detected_sections = db.Column(db.Text)
    education_analysis = db.Column(db.Text)
    ai_analysis = db.Column(db.Text)

    hr_decision = db.Column(db.String(80), default="Pending Manual Review")

    email_sent = db.Column(db.Boolean, default=False)
    email_locked = db.Column(db.Boolean, default=False)
    email_sent_at = db.Column(db.DateTime)
    email_sent_by = db.Column(db.Integer, db.ForeignKey("user.id"))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class EmailLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    candidate_id = db.Column(db.Integer, db.ForeignKey("candidate.id"), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id"), nullable=False)

    recipient_email = db.Column(db.String(160), nullable=False)
    email_type = db.Column(db.String(50))
    subject = db.Column(db.String(255))

    sent_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)

    status = db.Column(db.String(50), default="sent")
    message = db.Column(db.Text)