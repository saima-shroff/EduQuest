from email_validator import EmailNotValidError, validate_email
from flask import abort, jsonify
from flask_security import current_user, hash_password, verify_and_update_password
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..security import user_datastore
from . import api
from .common import payload, required_text, token_required


def user_json(user):
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "roles": [role.name for role in user.roles],
        "instructor_approved": user.instructor_approved,
    }


@api.post("/auth/register")
def register():
    data = payload()
    name = required_text(data, "name", 120)
    email = required_text(data, "email", 255).lower()
    password = data.get("password")
    if not isinstance(password, str) or len(password) < 8:
        abort(400, description="Password must be at least 8 characters.")
    selected_role = data.get("role")
    if selected_role not in ("Student", "Instructor"):
        abort(400, description="'role' must be Student or Instructor.")
    try:
        email = validate_email(email, check_deliverability=False).normalized.lower()
    except EmailNotValidError:
        abort(400, description="Enter a valid email address.")
    if user_datastore.find_user(email=email):
        abort(409, description="An account with this email already exists.")
    role = user_datastore.find_role(selected_role)
    if not role:
        abort(500, description="Database roles are not initialized. Run 'flask init-db'.")
    user = user_datastore.create_user(
        email=email,
        name=name,
        password=hash_password(password),
        roles=[role],
        instructor_approved=selected_role == "Student",
    )
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(409, description="An account with this email already exists.")
    return jsonify(user=user_json(user)), 201


@api.post("/auth/login")
def login():
    data = payload()
    email = data.get("email")
    password = data.get("password")
    if not isinstance(email, str) or not isinstance(password, str):
        abort(400, description="Email and password are required.")
    user = user_datastore.find_user(email=email.strip().lower())
    if not user or not user.active or not verify_and_update_password(password, user):
        abort(401, description="Invalid email or password.")
    if user.has_role("Instructor") and not user.instructor_approved:
        abort(403, description="Your instructor account is awaiting admin approval.")
    db.session.commit()
    return jsonify(auth_token=user.get_auth_token(), user=user_json(user))


@api.get("/auth/me")
@token_required
def me():
    return jsonify(user=user_json(current_user))
