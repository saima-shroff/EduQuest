from datetime import datetime, timezone

from flask_security import RoleMixin, UserMixin
from sqlalchemy import CheckConstraint, UniqueConstraint

from .extensions import db

roles_users = db.Table(
    "roles_users",
    db.Column("user_id", db.Integer(), db.ForeignKey("user.id"), primary_key=True),
    db.Column("role_id", db.Integer(), db.ForeignKey("role.id"), primary_key=True),
)


class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(255))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean(), nullable=False, default=True)
    instructor_approved = db.Column(db.Boolean(), nullable=False, default=False)
    fs_uniquifier = db.Column(db.String(64), unique=True, nullable=False)
    confirmed_at = db.Column(db.DateTime())
    roles = db.relationship("Role", secondary=roles_users, backref="users")


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    instructor_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    created_at = db.Column(
        db.DateTime, nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )
    instructor = db.relationship("User", backref="courses")
    chapters = db.relationship(
        "Chapter", back_populates="course", cascade="all, delete-orphan",
        order_by="Chapter.sequence_order",
    )


class Chapter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)
    title = db.Column(db.String(160), nullable=False)
    sequence_order = db.Column(db.Integer, nullable=False, default=1)
    course = db.relationship("Course", back_populates="chapters")
    quizzes = db.relationship("Quiz", back_populates="chapter", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("sequence_order > 0", name="ck_chapter_sequence_positive"),
    )


class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chapter_id = db.Column(db.Integer, db.ForeignKey("chapter.id"), nullable=False)
    title = db.Column(db.String(160), nullable=False)
    time_limit_minutes = db.Column(db.Integer, nullable=False, default=30)
    passing_score = db.Column(db.Float, nullable=False, default=60)
    chapter = db.relationship("Chapter", back_populates="quizzes")
    questions = db.relationship("Question", back_populates="quiz", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "time_limit_minutes > 0 AND time_limit_minutes <= 1440",
            name="ck_quiz_time_range",
        ),
        CheckConstraint("passing_score >= 0 AND passing_score <= 100", name="ck_quiz_pass_range"),
    )


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quiz.id"), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(30), nullable=False)
    points = db.Column(db.Float, nullable=False, default=1)
    accepted_answers = db.Column(db.JSON, nullable=False, default=list)
    quiz = db.relationship("Quiz", back_populates="questions")
    options = db.relationship("Option", back_populates="question", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("question_type IN ('Multiple-Choice', 'Short-Answer')", name="ck_question_type"),
        CheckConstraint("points > 0", name="ck_question_points_positive"),
    )


class Option(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey("question.id"), nullable=False)
    option_text = db.Column(db.String(500), nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False, default=False)
    question = db.relationship("Question", back_populates="options")


class Attempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quiz.id"), nullable=False)
    start_time = db.Column(
        db.DateTime, nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )
    end_time = db.Column(db.DateTime)
    total_score = db.Column(db.Float)
    status = db.Column(db.String(20), nullable=False, default="InProgress")
    student = db.relationship("User", backref="attempts")
    quiz = db.relationship("Quiz", backref="attempts")
    answers = db.relationship(
        "AttemptAnswer", back_populates="attempt", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("status IN ('InProgress', 'Submitted')", name="ck_attempt_status"),
    )


class AttemptAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey("attempt.id"), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("question.id"), nullable=False)
    student_response = db.Column(db.Text, nullable=False, default="")
    points_earned = db.Column(db.Float, nullable=False, default=0)
    is_correct = db.Column(db.Boolean, nullable=False, default=False)
    attempt = db.relationship("Attempt", back_populates="answers")
    question = db.relationship("Question")

    __table_args__ = (
        UniqueConstraint("attempt_id", "question_id", name="uq_attempt_question"),
    )
