import math

from flask import abort, jsonify
from flask_security import current_user
from sqlalchemy import func

from ..extensions import db
from ..models import Attempt, Chapter, Course, Option, Question, Quiz
from . import api
from .common import (
    get_owned_chapter, get_owned_quiz, payload, required_text, role_required,
    token_required,
)


def validate_question(data):
    if not isinstance(data, dict):
        abort(400, description="Each question must be a JSON object.")
    question_text = required_text(data, "question_text")
    question_type = data.get("question_type")
    if question_type not in ("Multiple-Choice", "Short-Answer"):
        abort(400, description="'question_type' must be Multiple-Choice or Short-Answer.")
    points = data.get("points", 1)
    if isinstance(points, bool) or not isinstance(points, (int, float)) or not math.isfinite(points) or points <= 0:
        abort(400, description="'points' must be a positive number.")

    question = Question(
        question_text=question_text,
        question_type=question_type,
        points=float(points),
    )
    if question_type == "Multiple-Choice":
        options = data.get("options")
        if not isinstance(options, list) or len(options) < 2:
            abort(400, description="Multiple-choice questions require at least two options.")
        correct_count = 0
        for option_data in options:
            if not isinstance(option_data, dict):
                abort(400, description="Each option must be a JSON object.")
            text = required_text(option_data, "option_text", 500)
            is_correct = option_data.get("is_correct", False)
            if not isinstance(is_correct, bool):
                abort(400, description="'is_correct' must be a boolean.")
            correct_count += is_correct
            question.options.append(Option(option_text=text, is_correct=is_correct))
        if correct_count != 1:
            abort(400, description="Exactly one multiple-choice option must be correct.")
        question.accepted_answers = []
    else:
        accepted = data.get("accepted_answers")
        if not isinstance(accepted, list) or not accepted:
            abort(400, description="Short-answer questions require at least one accepted answer.")
        if any(not isinstance(answer, str) or not answer.strip() for answer in accepted):
            abort(400, description="Accepted answers must be non-empty strings.")
        question.accepted_answers = [answer.strip() for answer in accepted]
    return question


def quiz_json(quiz, include_key=False):
    questions = []
    for question in quiz.questions:
        question_data = {
            "id": question.id,
            "question_text": question.question_text,
            "question_type": question.question_type,
            "points": question.points,
            "options": [
                {
                    "id": option.id,
                    "option_text": option.option_text,
                    **({"is_correct": option.is_correct} if include_key else {}),
                }
                for option in question.options
            ],
        }
        if include_key:
            question_data["accepted_answers"] = question.accepted_answers
        questions.append(question_data)
    return {
        "id": quiz.id,
        "chapter_id": quiz.chapter_id,
        "chapter_title": quiz.chapter.title,
        "course_id": quiz.chapter.course_id,
        "course_title": quiz.chapter.course.title,
        "title": quiz.title,
        "time_limit_minutes": quiz.time_limit_minutes,
        "passing_score": quiz.passing_score,
        "questions": questions,
        "max_points": sum(question.points for question in quiz.questions),
    }


def apply_quiz_payload(quiz, data, replace_questions=True):
    if "title" in data:
        quiz.title = required_text(data, "title", 160)
    elif not quiz.title:
        abort(400, description="'title' is required.")
    limit = data.get("time_limit_minutes", quiz.time_limit_minutes or 30)
    passing = data.get("passing_score", quiz.passing_score if quiz.passing_score is not None else 60)
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1 or limit > 1440:
        abort(400, description="'time_limit_minutes' must be between 1 and 1440.")
    if isinstance(passing, bool) or not isinstance(passing, (int, float)) or not math.isfinite(passing) or not 0 <= passing <= 100:
        abort(400, description="'passing_score' must be a number from 0 to 100.")
    quiz.time_limit_minutes = limit
    quiz.passing_score = float(passing)

    if replace_questions:
        questions = data.get("questions")
        if not isinstance(questions, list) or not questions:
            abort(400, description="A quiz must contain at least one question.")
        quiz.questions.clear()
        quiz.questions.extend(validate_question(item) for item in questions)


@api.get("/quizzes")
@token_required
def list_quizzes():
    query = Quiz.query.join(Chapter).join(Course)
    if current_user.has_role("Instructor"):
        query = query.filter(Course.instructor_id == current_user.id)
    quizzes = query.order_by(Quiz.id.desc()).all()
    return jsonify(quizzes=[
        quiz_json(quiz, include_key=current_user.has_role("Instructor"))
        for quiz in quizzes
    ])


@api.post("/quizzes")
@token_required
def create_quiz():
    role_required("Instructor")
    data = payload()
    chapter_id = data.get("chapter_id")
    if not isinstance(chapter_id, int) or isinstance(chapter_id, bool):
        abort(400, description="'chapter_id' must be an integer.")
    chapter = get_owned_chapter(chapter_id)
    quiz = Quiz(chapter_id=chapter.id, title="")
    apply_quiz_payload(quiz, data)
    db.session.add(quiz)
    db.session.commit()
    return jsonify(quiz=quiz_json(quiz, include_key=True)), 201


@api.get("/quizzes/<int:quiz_id>")
@token_required
def get_quiz(quiz_id):
    quiz = db.session.get(Quiz, quiz_id)
    if not quiz:
        abort(404, description="Quiz not found.")
    include_key = current_user.has_role("Instructor") and quiz.chapter.course.instructor_id == current_user.id
    return jsonify(quiz=quiz_json(quiz, include_key=include_key))


@api.put("/quizzes/<int:quiz_id>")
@token_required
def update_quiz(quiz_id):
    role_required("Instructor")
    quiz = get_owned_quiz(quiz_id)
    data = payload()
    attempt_count = db.session.scalar(
        db.select(func.count(Attempt.id)).where(Attempt.quiz_id == quiz.id)
    )
    if attempt_count and any(
        field in data for field in ("questions", "time_limit_minutes", "passing_score")
    ):
        abort(409, description="Questions and timing/scoring settings are locked after an attempt starts.")
    apply_quiz_payload(quiz, data, replace_questions="questions" in data)
    db.session.commit()
    return jsonify(quiz=quiz_json(quiz, include_key=True))


@api.delete("/quizzes/<int:quiz_id>")
@token_required
def delete_quiz(quiz_id):
    role_required("Instructor")
    quiz = get_owned_quiz(quiz_id)
    if db.session.scalar(db.select(func.count(Attempt.id)).where(Attempt.quiz_id == quiz.id)):
        abort(409, description="Quizzes with attempts cannot be deleted.")
    db.session.delete(quiz)
    db.session.commit()
    return jsonify(message="Quiz deleted.")
