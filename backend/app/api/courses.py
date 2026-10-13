from flask import abort, jsonify
from flask_security import current_user
from sqlalchemy import func

from ..extensions import db
from ..models import Attempt, Chapter, Course, Quiz
from . import api
from .common import (
    get_owned_course, payload, required_text, role_required, token_required,
)


def course_json(course, details=False):
    result = {
        "id": course.id,
        "instructor_id": course.instructor_id,
        "instructor_name": course.instructor.name,
        "title": course.title,
        "description": course.description,
        "created_at": course.created_at.isoformat() + "Z",
        "chapter_count": len(course.chapters),
    }
    if details:
        result["chapters"] = [
            {
                "id": chapter.id,
                "title": chapter.title,
                "sequence_order": chapter.sequence_order,
                "quizzes": [
                    {"id": quiz.id, "title": quiz.title, "question_count": len(quiz.questions)}
                    for quiz in chapter.quizzes
                ],
            }
            for chapter in course.chapters
        ]
    return result


@api.get("/courses")
@token_required
def list_courses():
    query = Course.query
    if current_user.has_role("Instructor"):
        query = query.filter_by(instructor_id=current_user.id)
    courses = query.order_by(Course.created_at.desc()).all()
    return jsonify(courses=[course_json(course) for course in courses])


@api.post("/courses")
@token_required
def create_course():
    role_required("Instructor")
    data = payload()
    course = Course(
        instructor_id=current_user.id,
        title=required_text(data, "title", 160),
    )
    course.description = data.get("description", "")
    if not isinstance(course.description, str):
        abort(400, description="'description' must be a string.")
    db.session.add(course)
    db.session.commit()
    return jsonify(course=course_json(course, details=True)), 201


@api.get("/courses/<int:course_id>")
@token_required
def get_course(course_id):
    course = db.session.get(Course, course_id)
    if not course:
        abort(404, description="Course not found.")
    return jsonify(course=course_json(course, details=True))


@api.put("/courses/<int:course_id>")
@token_required
def update_course(course_id):
    role_required("Instructor")
    course = get_owned_course(course_id)
    data = payload()
    if "title" in data:
        course.title = required_text(data, "title", 160)
    if "description" in data:
        if not isinstance(data["description"], str):
            abort(400, description="'description' must be a string.")
        course.description = data["description"]
    db.session.commit()
    return jsonify(course=course_json(course, details=True))


@api.delete("/courses/<int:course_id>")
@token_required
def delete_course(course_id):
    role_required("Instructor")
    course = get_owned_course(course_id)
    attempt_count = db.session.scalar(
        db.select(func.count(Attempt.id)).select_from(Attempt).join(Quiz).join(Chapter)
        .where(Chapter.course_id == course.id)
    )
    if attempt_count:
        abort(409, description="Courses with quiz attempts cannot be deleted.")
    db.session.delete(course)
    db.session.commit()
    return jsonify(message="Course deleted.")


@api.post("/courses/<int:course_id>/chapters")
@token_required
def create_chapter(course_id):
    role_required("Instructor")
    course = get_owned_course(course_id)
    data = payload()
    sequence = data.get("sequence_order", len(course.chapters) + 1)
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
        abort(400, description="'sequence_order' must be a positive integer.")
    chapter = Chapter(
        course_id=course.id,
        title=required_text(data, "title", 160),
        sequence_order=sequence,
    )
    db.session.add(chapter)
    db.session.commit()
    return jsonify(chapter={
        "id": chapter.id, "course_id": chapter.course_id, "title": chapter.title,
        "sequence_order": chapter.sequence_order,
    }), 201


@api.get("/courses/<int:course_id>/chapters")
@token_required
def list_chapters(course_id):
    course = db.session.get(Course, course_id)
    if not course:
        abort(404, description="Course not found.")
    chapters = Chapter.query.filter_by(course_id=course.id).order_by(Chapter.sequence_order).all()
    return jsonify(chapters=[
        {
            "id": chapter.id, "course_id": chapter.course_id, "title": chapter.title,
            "sequence_order": chapter.sequence_order,
            "quizzes": [{"id": quiz.id, "title": quiz.title} for quiz in chapter.quizzes],
        }
        for chapter in chapters
    ])
