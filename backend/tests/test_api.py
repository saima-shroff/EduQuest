import os
import sys
import unittest
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import create_app
from app.extensions import db
from app.models import Attempt
from app.security import user_datastore
from app.api.common import utcnow


class EduQuestApiTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "SECRET_KEY": "test-secret",
            "SECURITY_PASSWORD_SALT": "test-salt",
            "SECURITY_PASSWORD_HASH": "pbkdf2_sha256",
            "WTF_CSRF_ENABLED": False,
        })
        with self.app.app_context():
            db.create_all()
            user_datastore.create_role(name="Student")
            user_datastore.create_role(name="Instructor")
            self.student = user_datastore.create_user(
                email="student@example.com", name="Student", password="test-password",
                roles=[user_datastore.find_role("Student")],
            )
            self.instructor = user_datastore.create_user(
                email="teacher@example.com", name="Teacher", password="test-password",
                roles=[user_datastore.find_role("Instructor")],
            )
            self.other_instructor = user_datastore.create_user(
                email="other@example.com", name="Other", password="test-password",
                roles=[user_datastore.find_role("Instructor")],
            )
            db.session.commit()
        self.client = self.app.test_client()
        self.student_headers = self.login("student@example.com")
        self.instructor_headers = self.login("teacher@example.com")
        self.other_headers = self.login("other@example.com")

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def login(self, email):
        response = self.client.post("/api/auth/login", json={
            "email": email, "password": "test-password",
        })
        self.assertEqual(response.status_code, 200, response.get_json())
        return {"Authentication-Token": response.get_json()["auth_token"]}

    def create_quiz(self):
        course_response = self.client.post(
            "/api/courses", headers=self.instructor_headers,
            json={"title": "Foundations", "description": "Basics"},
        )
        self.assertEqual(course_response.status_code, 201, course_response.get_json())
        course_id = course_response.get_json()["course"]["id"]
        chapter_response = self.client.post(
            f"/api/courses/{course_id}/chapters", headers=self.instructor_headers,
            json={"title": "First steps"},
        )
        self.assertEqual(chapter_response.status_code, 201, chapter_response.get_json())
        chapter_id = chapter_response.get_json()["chapter"]["id"]
        quiz_response = self.client.post(
            "/api/quizzes", headers=self.instructor_headers,
            json={
                "chapter_id": chapter_id,
                "title": "Quick check",
                "time_limit_minutes": 15,
                "passing_score": 50,
                "questions": [
                    {
                        "question_text": "Pick the right option",
                        "question_type": "Multiple-Choice",
                        "points": 2,
                        "options": [
                            {"option_text": "Correct", "is_correct": True},
                            {"option_text": "Wrong", "is_correct": False},
                        ],
                    },
                    {
                        "question_text": "Type the answer",
                        "question_type": "Short-Answer",
                        "points": 3,
                        "accepted_answers": ["Edu Quest", "EDUQUEST"],
                    },
                ],
            },
        )
        self.assertEqual(quiz_response.status_code, 201, quiz_response.get_json())
        return course_id, chapter_id, quiz_response.get_json()["quiz"]

    def test_registration_cannot_assign_instructor_role(self):
        response = self.client.post("/api/auth/register", json={
            "name": "New person", "email": "new@example.com",
            "password": "password-123", "role": "Instructor",
        })
        self.assertEqual(response.status_code, 400)
        with self.app.app_context():
            self.assertIsNone(user_datastore.find_user(email="new@example.com"))

    def test_api_requires_token_and_returns_json_error(self):
        response = self.client.get("/api/courses")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json(), {"error": "Authentication required."})

    def test_mutations_require_role_and_course_ownership(self):
        course_id, _, _ = self.create_quiz()
        denied_role = self.client.post(
            "/api/courses", headers=self.student_headers,
            json={"title": "Not allowed"},
        )
        self.assertEqual(denied_role.status_code, 403)
        denied_owner = self.client.put(
            f"/api/courses/{course_id}", headers=self.other_headers,
            json={"title": "Changed"},
        )
        self.assertEqual(denied_owner.status_code, 403)

    def test_instructors_only_list_their_own_courses(self):
        self.client.post(
            "/api/courses", headers=self.instructor_headers,
            json={"title": "Teacher's course"},
        )
        self.client.post(
            "/api/courses", headers=self.other_headers,
            json={"title": "Other teacher's course"},
        )
        instructor_courses = self.client.get(
            "/api/courses", headers=self.instructor_headers,
        ).get_json()["courses"]
        student_courses = self.client.get(
            "/api/courses", headers=self.student_headers,
        ).get_json()["courses"]
        self.assertEqual([course["title"] for course in instructor_courses], ["Teacher's course"])
        self.assertEqual(len(student_courses), 2)

    def test_quiz_key_is_hidden_from_students_and_non_owner_instructors(self):
        _, _, quiz = self.create_quiz()
        student_response = self.client.get(
            f"/api/quizzes/{quiz['id']}", headers=self.student_headers,
        ).get_json()["quiz"]
        self.assertNotIn("is_correct", student_response["questions"][0]["options"][0])
        self.assertNotIn("accepted_answers", student_response["questions"][1])

        owner_response = self.client.get(
            f"/api/quizzes/{quiz['id']}", headers=self.instructor_headers,
        ).get_json()["quiz"]
        self.assertIn("is_correct", owner_response["questions"][0]["options"][0])
        self.assertIn("accepted_answers", owner_response["questions"][1])

        outsider_response = self.client.get(
            f"/api/quizzes/{quiz['id']}", headers=self.other_headers,
        ).get_json()["quiz"]
        self.assertNotIn("is_correct", outsider_response["questions"][0]["options"][0])

    def test_quiz_timing_and_scoring_are_locked_after_attempt_start(self):
        _, _, quiz = self.create_quiz()
        updated = self.client.put(
            f"/api/quizzes/{quiz['id']}", headers=self.instructor_headers,
            json={"time_limit_minutes": 10},
        )
        self.assertEqual(updated.status_code, 200, updated.get_json())
        self.assertEqual(updated.get_json()["quiz"]["time_limit_minutes"], 10)
        started = self.client.post(
            f"/api/quizzes/{quiz['id']}/start", headers=self.student_headers,
        )
        self.assertEqual(started.status_code, 201, started.get_json())
        self.assertEqual(
            self.client.delete(f"/api/quizzes/{quiz['id']}", headers=self.instructor_headers).status_code,
            409,
        )
        self.assertEqual(
            self.client.delete(f"/api/courses/{quiz['course_id']}", headers=self.instructor_headers).status_code,
            409,
        )
        for body in (
            {"time_limit_minutes": 20},
            {"passing_score": 75},
            {"questions": []},
        ):
            response = self.client.put(
                f"/api/quizzes/{quiz['id']}", headers=self.instructor_headers,
                json=body,
            )
            self.assertEqual(response.status_code, 409, response.get_json())

    def test_instructor_can_delete_empty_quiz_and_course(self):
        course_id, _, quiz = self.create_quiz()
        deleted_quiz = self.client.delete(
            f"/api/quizzes/{quiz['id']}", headers=self.instructor_headers,
        )
        self.assertEqual(deleted_quiz.status_code, 200, deleted_quiz.get_json())
        self.assertEqual(
            self.client.get(f"/api/quizzes/{quiz['id']}", headers=self.student_headers).status_code,
            404,
        )
        deleted_course = self.client.delete(
            f"/api/courses/{course_id}", headers=self.instructor_headers,
        )
        self.assertEqual(deleted_course.status_code, 200, deleted_course.get_json())

    def test_student_answers_are_graded_and_attempt_is_private(self):
        _, _, quiz = self.create_quiz()
        started = self.client.post(
            f"/api/quizzes/{quiz['id']}/start", headers=self.student_headers,
        )
        self.assertEqual(started.status_code, 201, started.get_json())
        attempt_id = started.get_json()["attempt"]["id"]
        mc_question, short_question = quiz["questions"]
        correct_option = next(option for option in mc_question["options"] if option["is_correct"])
        saved = self.client.put(
            f"/api/attempts/{attempt_id}/answers",
            headers=self.student_headers,
            json={"answers": [
                {"question_id": mc_question["id"], "student_response": str(correct_option["id"])},
                {"question_id": short_question["id"], "student_response": "  edu   quest "},
            ]},
        )
        self.assertEqual(saved.status_code, 200, saved.get_json())
        submitted = self.client.post(
            f"/api/attempts/{attempt_id}/submit", headers=self.student_headers,
            json={"answers": []},
        )
        self.assertEqual(submitted.status_code, 200, submitted.get_json())
        result = submitted.get_json()["attempt"]
        self.assertEqual(result["total_score"], 5)
        self.assertEqual(result["score_percentage"], 100)
        self.assertEqual(result["status"], "Submitted")
        denied = self.client.get(
            f"/api/attempts/{attempt_id}", headers=self.other_headers,
        )
        self.assertEqual(denied.status_code, 403)

    def test_late_submission_ignores_unsaved_answers_and_finalizes(self):
        _, _, quiz = self.create_quiz()
        started = self.client.post(
            f"/api/quizzes/{quiz['id']}/start", headers=self.student_headers,
        ).get_json()["attempt"]
        with self.app.app_context():
            attempt = db.session.get(Attempt, started["id"])
            attempt.start_time = utcnow() - timedelta(minutes=20)
            attempt_id = attempt.id
            db.session.commit()

        question = quiz["questions"][0]
        correct_option = next(option for option in question["options"] if option["is_correct"])
        response = self.client.post(
            f"/api/attempts/{attempt_id}/submit",
            headers=self.student_headers,
            json={"answers": [{
                "question_id": question["id"],
                "student_response": str(correct_option["id"]),
            }]},
        )
        self.assertEqual(response.status_code, 200, response.get_json())
        result = response.get_json()["attempt"]
        self.assertEqual(result["total_score"], 0)
        self.assertEqual(result["status"], "Submitted")


if __name__ == "__main__":
    unittest.main()
