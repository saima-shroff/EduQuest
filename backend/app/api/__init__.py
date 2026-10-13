from flask import Blueprint

api = Blueprint("api", __name__)

from . import auth, courses, quizzes, attempts  # noqa: E402,F401
