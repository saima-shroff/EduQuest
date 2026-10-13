from flask import Blueprint

api = Blueprint("api", __name__)

from . import admin, auth, courses, quizzes, attempts  # noqa: E402,F401
