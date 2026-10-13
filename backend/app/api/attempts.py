import unicodedata
from datetime import timedelta

from flask import abort, jsonify
from flask_security import current_user

from ..extensions import db
from ..models import Attempt, AttemptAnswer, Quiz
from . import api
from .common import iso_utc, payload, role_required, token_required, utcnow
from .quizzes import quiz_json


def deadline(attempt):
    return attempt.start_time + timedelta(minutes=attempt.quiz.time_limit_minutes)


def normalize_answer(value):
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def owned_attempt(attempt_id):
    attempt = db.session.get(Attempt, attempt_id)
    if not attempt:
        abort(404, description="Attempt not found.")
    if attempt.student_id != current_user.id:
        abort(403, description="You do not own this attempt.")
    return attempt


def attempt_json(attempt):
    max_points = sum(question.points for question in attempt.quiz.questions)
    result = {
        "id": attempt.id,
        "student_id": attempt.student_id,
        "quiz_id": attempt.quiz_id,
        "quiz_title": attempt.quiz.title,
        "passing_score": attempt.quiz.passing_score,
        "start_time": iso_utc(attempt.start_time),
        "end_time": iso_utc(attempt.end_time),
        "deadline": iso_utc(deadline(attempt)),
        "status": attempt.status,
        "total_score": attempt.total_score,
        "max_points": max_points,
        "score_percentage": round((attempt.total_score or 0) / max_points * 100, 2) if max_points else 0,
        "answers": {
            str(answer.question_id): answer.student_response for answer in attempt.answers
        },
    }
    if attempt.status == "Submitted":
        result["answer_results"] = {
            str(answer.question_id): {
                "is_correct": answer.is_correct,
                "points_earned": answer.points_earned,
            }
            for answer in attempt.answers
        }
    return result


def save_answers(attempt, answers):
    if not isinstance(answers, list):
        abort(400, description="'answers' must be a list.")
    questions = {question.id: question for question in attempt.quiz.questions}
    indexed = {}
    for item in answers:
        if not isinstance(item, dict):
            abort(400, description="Each answer must be a JSON object.")
        question_id = item.get("question_id")
        response = item.get("student_response", "")
        if not isinstance(question_id, int) or isinstance(question_id, bool):
            abort(400, description="'question_id' must be an integer.")
        if question_id not in questions:
            abort(400, description="An answer references a question outside this quiz.")
        if not isinstance(response, str):
            abort(400, description="'student_response' must be a string.")
        if len(response) > 10000:
            abort(400, description="An answer cannot exceed 10000 characters.")
        if question_id in indexed:
            abort(400, description="Each question may appear only once in an answer submission.")
        indexed[question_id] = response.strip()

    current = {answer.question_id: answer for answer in attempt.answers}
    for question_id, response in indexed.items():
        answer = current.get(question_id)
        if answer:
            answer.student_response = response
        else:
            attempt.answers.append(AttemptAnswer(
                question_id=question_id, student_response=response
            ))


def finalize(attempt, submitted_at=None):
    if attempt.status == "Submitted":
        return
    answer_by_question = {answer.question_id: answer for answer in attempt.answers}
    total = 0.0
    for question in attempt.quiz.questions:
        answer = answer_by_question.get(question.id)
        response = answer.student_response.strip() if answer else ""
        correct = False
        if question.question_type == "Multiple-Choice":
            correct_option = next(option for option in question.options if option.is_correct)
            correct = response == str(correct_option.id)
        else:
            accepted = {normalize_answer(item) for item in question.accepted_answers}
            correct = bool(response) and normalize_answer(response) in accepted
        earned = question.points if correct else 0.0
        if not answer:
            answer = AttemptAnswer(
                question_id=question.id, student_response="", points_earned=0, is_correct=False
            )
            attempt.answers.append(answer)
        answer.is_correct = correct
        answer.points_earned = earned
        total += earned
    attempt.total_score = total
    attempt.status = "Submitted"
    attempt.end_time = submitted_at or utcnow()


@api.post("/quizzes/<int:quiz_id>/start")
@token_required
def start_attempt(quiz_id):
    role_required("Student")
    quiz = db.session.get(Quiz, quiz_id)
    if not quiz:
        abort(404, description="Quiz not found.")
    existing = Attempt.query.filter_by(
        student_id=current_user.id, quiz_id=quiz.id, status="InProgress"
    ).first()
    if existing:
        abort(409, description=f"An attempt is already in progress (attempt_id={existing.id}).")
    attempt = Attempt(
        student_id=current_user.id, quiz_id=quiz.id, start_time=utcnow()
    )
    db.session.add(attempt)
    db.session.commit()
    return jsonify(attempt=attempt_json(attempt), quiz=quiz_json(quiz)), 201


@api.get("/attempts/<int:attempt_id>")
@token_required
def get_attempt(attempt_id):
    role_required("Student")
    attempt = owned_attempt(attempt_id)
    if attempt.status == "InProgress" and utcnow() >= deadline(attempt):
        finalize(attempt, submitted_at=deadline(attempt))
        db.session.commit()
    return jsonify(attempt=attempt_json(attempt), quiz=quiz_json(attempt.quiz))


@api.put("/attempts/<int:attempt_id>/answers")
@token_required
def update_attempt_answers(attempt_id):
    role_required("Student")
    attempt = owned_attempt(attempt_id)
    if attempt.status != "InProgress":
        abort(409, description="This attempt has already been submitted.")
    if utcnow() >= deadline(attempt):
        finalize(attempt, submitted_at=deadline(attempt))
        db.session.commit()
        abort(409, description="Time expired; saved answers were submitted.")
    data = payload()
    save_answers(attempt, data.get("answers"))
    db.session.commit()
    return jsonify(attempt=attempt_json(attempt))


@api.post("/attempts/<int:attempt_id>/submit")
@token_required
def submit_attempt(attempt_id):
    role_required("Student")
    attempt = owned_attempt(attempt_id)
    if attempt.status != "InProgress":
        abort(409, description="This attempt has already been submitted.")
    now = utcnow()
    if now < deadline(attempt):
        data = payload()
        save_answers(attempt, data.get("answers"))
        submitted_at = now
    else:
        submitted_at = deadline(attempt)
    finalize(attempt, submitted_at=submitted_at)
    db.session.commit()
    return jsonify(attempt=attempt_json(attempt))


@api.get("/attempts/history")
@token_required
def attempt_history():
    role_required("Student")
    attempts = Attempt.query.filter_by(student_id=current_user.id).order_by(Attempt.start_time.desc()).all()
    changed = False
    for attempt in attempts:
        if attempt.status == "InProgress" and utcnow() >= deadline(attempt):
            finalize(attempt, submitted_at=deadline(attempt))
            changed = True
    if changed:
        db.session.commit()
    return jsonify(attempts=[attempt_json(attempt) for attempt in attempts])
