import os
import click
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_security import hash_password
from flask_security.decorators import default_unauthn_handler

from .extensions import db, security as security_ext
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
    def init_db():
        """Create tables and the two supported roles."""
        db.create_all()
        for role_name in ("Instructor", "Student"):
            if not user_datastore.find_role(role_name):
                user_datastore.create_role(name=role_name)
        db.session.commit()
        click.echo("Database initialized.")

    @app.cli.command("promote-instructor")
    @click.argument("email")
    def promote_instructor(email):
        """Grant Instructor privileges to an existing account."""
        user = user_datastore.find_user(email=email.strip().lower())
        role = user_datastore.find_role("Instructor")
        if not user:
            raise click.ClickException("No account exists for that email.")
        if not role:
            raise click.ClickException("Run 'flask init-db' first.")
        if not user.has_role("Instructor"):
            user_datastore.add_role_to_user(user, role)
            db.session.commit()
        click.echo(f"Instructor role granted to {user.email}.")

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
