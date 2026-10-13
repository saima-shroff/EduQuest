# EduQuest

## Application overview and features

EduQuest is a quiz and assessment website I built to help students practice and instructors create learning materials. Courses can be organized into chapters, and each chapter can have timed quizzes with multiple-choice or short-answer questions.

Students can browse quizzes, save their answers while they work, submit their attempts, and check their scores and past results. Instructors can create and manage their own courses, chapters, quizzes, and questions. Quiz answers are graded automatically. Short answers are matched with accepted answers without considering differences in letter case or extra spaces.

The project uses Flask, SQLAlchemy, and Flask-Security-Too for the backend, and Vue 3, Vue Router, Axios, and Vite for the frontend. SQLite is used as the development database.

## Initial setup and installation

You will need Python 3.10 or newer and Node.js 20 or newer with npm.

### 1. Set up the backend

In PowerShell, from the project folder:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
flask --app run.py init-db
flask --app run.py run
```

The backend runs at `http://127.0.0.1:5000`. The database is created at `backend/instance/eduquest.db`.

Anyone can register as a Student. An existing account can be given Instructor access by a trusted operator:

```powershell
flask --app run.py promote-instructor instructor@example.com
```

### 2. Set up the frontend

Open a second PowerShell window:

```powershell
cd frontend
npm install
npm run dev
```

Open the address printed by Vite, usually `http://localhost:5173`. The frontend forwards API requests to the Flask server.

## API documentation

All requests and responses use JSON. Except for registration and login, endpoints require an authentication token in this header:

```http
Authentication-Token: <auth_token>
```

### Authentication

| Method | Endpoint | Who can use it | What it does |
|---|---|---|---|
| `POST` | `/api/auth/register` | Anyone | Register a Student with `{"name":"Sam","email":"sam@example.com","password":"at-least-8-chars"}` |
| `POST` | `/api/auth/login` | Anyone | Log in with email and password; returns the authentication token and user profile |
| `GET` | `/api/auth/me` | Signed-in users | Get the current user's profile and roles |

### Courses and chapters

| Method | Endpoint | Who can use it | What it does |
|---|---|---|---|
| `GET` | `/api/courses` | Signed-in users | List courses |
| `POST` | `/api/courses` | Instructors | Create a course with a title and description |
| `GET` | `/api/courses/<id>` | Signed-in users | Get a course, its chapters, and quiz summaries |
| `PUT` | `/api/courses/<id>` | Course owner | Update a course title or description |
| `DELETE` | `/api/courses/<id>` | Course owner | Delete a course if none of its quizzes have attempts |
| `GET` | `/api/courses/<course_id>/chapters` | Signed-in users | List a course's chapters |
| `POST` | `/api/courses/<course_id>/chapters` | Course owner | Add a chapter with a title and optional sequence order |

### Quizzes

| Method | Endpoint | Who can use it | What it does |
|---|---|---|---|
| `GET` | `/api/quizzes` | Signed-in users | List available quizzes |
| `POST` | `/api/quizzes` | Instructors | Create a quiz in a chapter they own |
| `GET` | `/api/quizzes/<id>` | Signed-in users | Get quiz questions; only the quiz's instructor sees correct answers |
| `PUT` | `/api/quizzes/<id>` | Quiz owner | Update a quiz |
| `DELETE` | `/api/quizzes/<id>` | Quiz owner | Delete a quiz if no attempts have started |
| `POST` | `/api/quizzes/<id>/start` | Students | Start a timed quiz attempt |


Multiple-choice questions need at least two options and exactly one correct answer. Short-answer questions need at least one accepted answer. Once a student starts a quiz, its questions and scoring/timing settings are locked so the attempt stays consistent.

### Quiz attempts

| Method | Endpoint | Who can use it | What it does |
|---|---|---|---|
| `GET` | `/api/attempts/<attempt_id>` | Attempt owner | Get an attempt, saved answers, deadline, and quiz |
| `PUT` | `/api/attempts/<attempt_id>/answers` | Attempt owner | Save answers before time runs out |
| `POST` | `/api/attempts/<attempt_id>/submit` | Attempt owner | Submit answers and get the score |
| `GET` | `/api/attempts/history` | Students | View their own attempt history |


For multiple-choice questions, `student_response` is the selected option ID as text. The API checks that each answer belongs to the quiz. The browser timer is just a display; the server decides when time is up and automatically submits the answers already saved on the server.

API errors are returned as JSON, for example `{"error":"Authentication required."}`.
