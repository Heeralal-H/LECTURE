# Lecture2Learning

Lecture2Learning is a full-stack academic learning platform that:

1. Registers/logs in students.
2. Accepts lecture PDFs.
3. Extracts text from PDFs.
4. Detects topics using headings/keywords.
5. Generates topic-tagged MCQs and True/False questions.
6. Runs quizzes and automatically evaluates answers.
7. Produces topic-wise performance analysis.
8. Detects weak topics and recommends revision.
9. Tracks quiz history.

## Tech Stack

- Backend: Python, FastAPI, SQLAlchemy, SQLite
- PDF extraction: PyMuPDF
- Frontend: HTML, CSS, Vanilla JavaScript
- Authentication: bearer tokens stored in SQLite
- No external AI API is required for the base version.

## Project Structure

```text
Lecture2Learning/
├── backend/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   └── services/
│       ├── pdf_service.py
│       ├── topic_service.py
│       ├── quiz_service.py
│       └── report_service.py
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── uploads/
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

## Run locally

### Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

### Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Open:

http://127.0.0.1:8000

API documentation:

http://127.0.0.1:8000/docs

## Docker

```bash
docker compose up --build
```

Open http://localhost:8000

## Important

This is a complete academic project baseline, not a production security system. Before production deployment, add HTTPS, stronger authentication, rate limiting, antivirus/file scanning, background jobs, cloud storage, and a real LLM/vector database if desired.
