from flask import abort, jsonify
from flask_security import current_user
from sqlalchemy import func

from ..extensions import db
from ..models import Attempt, Course, Quiz, Role, User
from . import api
from .common import role_required, token_required, utcnow


def user_has_role_query(role_name):
    return (
        db.select(User.id)
        .join(User.roles)
        .where(Role.name == role_name)
    )


@api.get("/admin/dashboard")
@token_required
def admin_dashboard():
    role_required("Admin")
    student_count = db.session.scalar(
        db.select(func.count(User.id)).where(
            User.id.in_(user_has_role_query("Student"))
        )
    )
    instructor_query = db.select(User).where(User.id.in_(user_has_role_query("Instructor")))
    instructors = db.session.scalars(instructor_query.order_by(User.id.desc())).all()
    pending = [
        user for user in instructors
        if user.active and not user.instructor_approved
    ]
    approved_instructors = [
        user for user in instructors
        if user.active and user.instructor_approved
    ]
    attempt_counts = db.session.execute(
        db.select(Attempt.status, func.count(Attempt.id)).group_by(Attempt.status)
    ).all()
    attempt_counts = dict(attempt_counts)
    submitted_attempts = Attempt.query.filter_by(status="Submitted").all()
    score_percentages = []
    for attempt in submitted_attempts:
        max_points = sum(question.points for question in attempt.quiz.questions)
        if max_points:
            score_percentages.append((attempt.total_score or 0) / max_points * 100)

    quizzes = Quiz.query.order_by(Quiz.id.desc()).limit(100).all()
    quiz_activity = []
    for quiz in quizzes:
        course = quiz.chapter.course
        quiz_activity.append({
            "id": quiz.id,
            "title": quiz.title,
            "course_title": course.title,
            "chapter_title": quiz.chapter.title,
            "instructor_id": course.instructor_id,
            "instructor_name": course.instructor.name,
            "instructor_email": course.instructor.email,
            "question_count": len(quiz.questions),
            "attempt_count": len(quiz.attempts),
            "time_limit_minutes": quiz.time_limit_minutes,
        })

    attempts = Attempt.query.order_by(Attempt.start_time.desc()).limit(100).all()
    attempt_activity = []
    for attempt in attempts:
        max_points = sum(question.points for question in attempt.quiz.questions)
        attempt_activity.append({
            "id": attempt.id,
            "student_id": attempt.student_id,
            "student_name": attempt.student.name,
            "student_email": attempt.student.email,
            "quiz_id": attempt.quiz_id,
            "quiz_title": attempt.quiz.title,
            "instructor_name": attempt.quiz.chapter.course.instructor.name,
            "status": attempt.status,
            "start_time": attempt.start_time.isoformat() + "Z",
            "end_time": attempt.end_time.isoformat() + "Z" if attempt.end_time else None,
            "total_score": attempt.total_score,
            "max_points": max_points,
            "score_percentage": (
                round((attempt.total_score or 0) / max_points * 100, 2)
                if max_points else 0
            ),
        })

    return jsonify({
        "generated_at": utcnow().isoformat() + "Z",
        "stats": {
            "students": student_count,
            "instructors": len(approved_instructors),
            "pending_instructors": len(pending),
            "courses": Course.query.count(),
            "active_quizzes": Quiz.query.count(),
            "total_attempts": Attempt.query.count(),
            "in_progress_attempts": attempt_counts.get("InProgress", 0),
            "submitted_attempts": attempt_counts.get("Submitted", 0),
            "average_score_percentage": (
                round(sum(score_percentages) / len(score_percentages), 2)
                if score_percentages else 0
            ),
        },
        "pending_instructors": [
            {
                "id": user.id,
                "name": user.name,
                "email": user.email,
            }
            for user in pending
        ],
        "quizzes": quiz_activity,
        "recent_attempts": attempt_activity,
        "current_admin": {
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email,
        },
    })


@api.post("/admin/instructors/<int:user_id>/approve")
@token_required
def approve_instructor(user_id):
    role_required("Admin")
    user = db.session.get(User, user_id)
    if not user or not user.has_role("Instructor"):
        abort(404, description="Pending instructor not found.")
    if user.instructor_approved:
        abort(409, description="This instructor has already been approved.")
    user.instructor_approved = True
    db.session.commit()
    return jsonify(message="Instructor approved.", instructor={
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "instructor_approved": True,
    })
