from datetime import datetime, timezone
from functools import wraps

from flask import abort, request
from flask_security import auth_required, current_user

from ..extensions import db
from ..models import Chapter, Course, Quiz


def token_required(view):
    @wraps(view)
    @auth_required("token")
    def wrapped(*args, **kwargs):
        if current_user.has_role("Instructor") and not current_user.instructor_approved:
            abort(403, description="Your instructor account is awaiting admin approval.")
        return view(*args, **kwargs)

    return wrapped


def role_required(role_name):
    if not current_user.has_role(role_name):
        abort(403, description=f"{role_name} role required.")


def payload():
    value = request.get_json()
    if not isinstance(value, dict):
        abort(400, description="Request body must be a JSON object.")
    return value


def required_text(data, key, max_length=None):
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        abort(400, description=f"'{key}' must be a non-empty string.")
    value = value.strip()
    if max_length and len(value) > max_length:
        abort(400, description=f"'{key}' must be at most {max_length} characters.")
    return value


def get_owned_course(course_id):
    course = db.session.get(Course, course_id)
    if not course:
        abort(404, description="Course not found.")
    if course.instructor_id != current_user.id:
        abort(403, description="You do not own this course.")
    return course


def get_owned_chapter(chapter_id):
    chapter = db.session.get(Chapter, chapter_id)
    if not chapter:
        abort(404, description="Chapter not found.")
    if chapter.course.instructor_id != current_user.id:
        abort(403, description="You do not own this chapter's course.")
    return chapter


def get_owned_quiz(quiz_id):
    quiz = db.session.get(Quiz, quiz_id)
    if not quiz:
        abort(404, description="Quiz not found.")
    if quiz.chapter.course.instructor_id != current_user.id:
        abort(403, description="You do not own this quiz's course.")
    return quiz


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso_utc(value):
    return value.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z") if value else None
