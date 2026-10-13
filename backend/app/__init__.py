import os
import click
from email_validator import EmailNotValidError, validate_email
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_security import hash_password
from flask_security.decorators import default_unauthn_handler
from sqlalchemy import func, inspect, text

from .extensions import db, security as security_ext
from .models import Role, User
from .security import user_datastore


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object("config.Config")
    if test_config:
        app.config.update(test_config)
    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    security_ext.init_app(app, user_datastore)

    def api_unauthenticated(mechanisms=None, headers=None):
        if request.path.startswith("/api/"):
            return jsonify(error="Authentication required."), 401
        return default_unauthn_handler(mechanisms, headers)

    security_ext.unauthn_handler(api_unauthenticated)
    CORS(app, resources={r"/api/*": {"origins": app.config.get("CORS_ORIGINS", "*")}})

    from .api import api

    app.register_blueprint(api, url_prefix="/api")

    @app.errorhandler(400)
    @app.errorhandler(401)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(409)
    @app.errorhandler(415)
    @app.errorhandler(500)
    def handle_api_error(error):
        return jsonify(error=error.description), error.code

    @app.cli.command("init-db")
    def init_db_command():
        """Create tables, application roles, and the first Admin account."""
        db.create_all()
        if "instructor_approved" not in {
            column["name"] for column in inspect(db.engine).get_columns("user")
        }:
            with db.engine.begin() as connection:
                connection.execute(text(
                    'ALTER TABLE "user" ADD COLUMN instructor_approved '
                    "BOOLEAN NOT NULL DEFAULT FALSE"
                ))
                connection.execute(text(
                    'UPDATE "user" SET instructor_approved = TRUE '
                    'WHERE id IN ('
                    'SELECT roles_users.user_id FROM roles_users '
                    'JOIN role ON role.id = roles_users.role_id '
                    "WHERE role.name = 'Instructor'"
                    ')'
                ))
            db.session.expire_all()

        for role_name in ("Admin", "Instructor", "Student"):
            if not user_datastore.find_role(role_name):
                user_datastore.create_role(name=role_name)
        db.session.commit()

        for user in db.session.scalars(db.select(User)).all():
            if not user.password.startswith("$"):
                user.password = hash_password(user.password)

        admin_count = db.session.scalar(
            db.select(func.count(User.id))
            .join(User.roles)
            .where(Role.name == "Admin")
        )
        if not admin_count:
            admin_email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
            admin_password = os.environ.get("ADMIN_PASSWORD", "")
            if not admin_email or len(admin_password) < 12:
                raise click.ClickException(
                    "No Admin account exists. Set ADMIN_EMAIL and ADMIN_PASSWORD "
                    "(at least 12 characters), then run 'flask init-db' again."
                )
            try:
                admin_email = validate_email(
                    admin_email, check_deliverability=False
                ).normalized.lower()
            except EmailNotValidError as error:
                raise click.ClickException(f"ADMIN_EMAIL is invalid: {error}") from error
            if user_datastore.find_user(email=admin_email):
                raise click.ClickException(
                    "ADMIN_EMAIL already belongs to a non-admin account."
                )
            user_datastore.create_user(
                email=admin_email,
                name="EduQuest Admin",
                password=hash_password(admin_password),
                roles=[user_datastore.find_role("Admin")],
                instructor_approved=True,
            )
        db.session.commit()
        click.echo("Database initialized. Admin account is ready.")

    @app.shell_context_processor
    def shell_context():
        from .models import Attempt, AttemptAnswer, Chapter, Course, Option, Question, Quiz, Role, User
        return {
            "db": db, "User": User, "Role": Role, "Course": Course,
            "Chapter": Chapter, "Quiz": Quiz, "Question": Question,
            "Option": Option, "Attempt": Attempt, "AttemptAnswer": AttemptAnswer,
            "hash_password": hash_password,
        }

    return app
