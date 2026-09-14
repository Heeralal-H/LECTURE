from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Header
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from pathlib import Path
from datetime import datetime
import hashlib, secrets, os, re

from .database import Base, engine, get_db
from .models import User, Lecture, Topic, Quiz, Question, QuizAttempt, UserAnswer
from .schemas import RegisterRequest, LoginRequest, SubmitQuizRequest
from .services.pdf_service import extract_pdf_text
from .services.topic_service import extract_topics, keywords_for_topic
from .services.quiz_service import generate_questions
from .services.report_service import build_report

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Lecture2Learning API", version="1.0.0")

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "20"))

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000)
    return salt.hex() + ":" + digest.hex()

def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split(":")
        salt = bytes.fromhex(salt_hex)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000).hex()
        return secrets.compare_digest(actual, digest_hex)
    except Exception:
        return False

def get_current_user(authorization: str | None, db: Session):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Authentication required")
    token = authorization.split(" ", 1)[1]
    user = db.query(User).filter(User.token == token).first()
    if not user:
        raise HTTPException(401, "Invalid or expired session")
    return user

@app.get("/")
def home():
    return FileResponse("frontend/index.html")

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "Lecture2Learning"}

@app.post("/api/auth/register")
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(400, "Email already registered")
    token = secrets.token_urlsafe(32)
    user = User(
        name=payload.name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
        token=token
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"token": token, "user": {"id": user.id, "name": user.name, "email": user.email}}

@app.post("/api/auth/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower().strip()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    user.token = secrets.token_urlsafe(32)
    db.commit()
    return {"token": user.token, "user": {"id": user.id, "name": user.name, "email": user.email}}

@app.post("/api/auth/logout")
def logout(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    user = get_current_user(authorization, db)
    user.token = None
    db.commit()
    return {"message": "Logged out"}

@app.get("/api/me")
def me(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    user = get_current_user(authorization, db)
    return {"id": user.id, "name": user.name, "email": user.email}

@app.post("/api/lectures/upload")
async def upload_lecture(
    file: UploadFile = File(...),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db)
):
    user = get_current_user(authorization, db)
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported")

    data = await file.read()
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(400, f"File exceeds {MAX_UPLOAD_MB} MB limit")

    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", file.filename)
    stored_name = f"{secrets.token_hex(8)}_{safe_name}"
    path = UPLOAD_DIR / stored_name
    path.write_bytes(data)

    try:
        text = extract_pdf_text(str(path))
    except Exception as exc:
        path.unlink(missing_ok=True)
        raise HTTPException(400, f"Could not read PDF: {exc}")

    if len(text.strip()) < 50:
        path.unlink(missing_ok=True)
        raise HTTPException(400, "The PDF contains too little extractable text. For scanned PDFs, add OCR support.")

    title = Path(file.filename).stem.replace("_", " ").strip()
    lecture = Lecture(
        user_id=user.id,
        title=title[:255],
        filename=stored_name,
        extracted_text=text
    )
    db.add(lecture)
    db.flush()

    topic_names = extract_topics(text)
    for name in topic_names:
        db.add(Topic(
            lecture_id=lecture.id,
            name=name[:255],
            keywords=keywords_for_topic(name, text),
            description=f"Automatically detected topic from the lecture: {name}"
        ))

    db.commit()
    db.refresh(lecture)
    return {
        "id": lecture.id,
        "title": lecture.title,
        "topics": topic_names,
        "pages_text_length": len(text)
    }

@app.get("/api/lectures")
def list_lectures(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    user = get_current_user(authorization, db)
    lectures = db.query(Lecture).filter(Lecture.user_id == user.id).order_by(desc(Lecture.created_at)).all()
    return [
        {
            "id": l.id,
            "title": l.title,
            "created_at": l.created_at.isoformat(),
            "topics": [t.name for t in l.topics]
        }
        for l in lectures
    ]

@app.delete("/api/lectures/{lecture_id}")
def delete_lecture(lecture_id: int, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    user = get_current_user(authorization, db)
    lecture = db.query(Lecture).filter(Lecture.id == lecture_id, Lecture.user_id == user.id).first()
    if not lecture:
        raise HTTPException(404, "Lecture not found")
    db.delete(lecture)
    db.commit()
    return {"message": "Lecture deleted"}

@app.post("/api/lectures/{lecture_id}/generate-quiz")
def create_quiz(
    lecture_id: int,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db)
):
    user = get_current_user(authorization, db)
    lecture = db.query(Lecture).filter(Lecture.id == lecture_id, Lecture.user_id == user.id).first()
    if not lecture:
        raise HTTPException(404, "Lecture not found")

    quiz = Quiz(lecture_id=lecture.id, title=f"{lecture.title} - Practice Quiz")
    db.add(quiz)
    db.flush()

    topics = db.query(Topic).filter(Topic.lecture_id == lecture.id).all()
    total = 0
    for topic in topics:
        generated = generate_questions(topic.name, lecture.extracted_text, count=4)
        for item in generated:
            q = Question(
                quiz_id=quiz.id,
                topic_id=topic.id,
                question_text=item["question_text"],
                question_type="mcq",
                option_a=item["options"][0],
                option_b=item["options"][1],
                option_c=item["options"][2],
                option_d=item["options"][3],
                correct_answer=item["correct_answer"],
                difficulty=item["difficulty"],
                explanation=item["explanation"]
            )
            db.add(q)
            total += 1

    if total == 0:
        db.rollback()
        raise HTTPException(400, "Could not generate questions from this lecture")

    db.commit()
    db.refresh(quiz)
    return {"quiz_id": quiz.id, "title": quiz.title, "question_count": total}

@app.get("/api/quizzes/{quiz_id}")
def get_quiz(quiz_id: int, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    user = get_current_user(authorization, db)
    quiz = (
        db.query(Quiz)
        .join(Lecture)
        .filter(Quiz.id == quiz_id, Lecture.user_id == user.id)
        .options(joinedload(Quiz.questions).joinedload(Question.topic))
        .first()
    )
    if not quiz:
        raise HTTPException(404, "Quiz not found")

    return {
        "id": quiz.id,
        "title": quiz.title,
        "lecture_id": quiz.lecture_id,
        "questions": [
            {
                "id": q.id,
                "topic": q.topic.name,
                "question_text": q.question_text,
                "question_type": q.question_type,
                "options": [q.option_a, q.option_b, q.option_c, q.option_d],
                "difficulty": q.difficulty
            }
            for q in quiz.questions
        ]
    }

@app.post("/api/quizzes/{quiz_id}/submit")
def submit_quiz(
    quiz_id: int,
    payload: SubmitQuizRequest,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db)
):
    user = get_current_user(authorization, db)
    quiz = (
        db.query(Quiz)
        .join(Lecture)
        .filter(Quiz.id == quiz_id, Lecture.user_id == user.id)
        .options(joinedload(Quiz.questions).joinedload(Question.topic))
        .first()
    )
    if not quiz:
        raise HTTPException(404, "Quiz not found")

    answer_map = {a.question_id: a.answer.strip() for a in payload.answers}
    correct = 0

    attempt = QuizAttempt(user_id=user.id, quiz_id=quiz.id, time_taken=payload.time_taken)
    db.add(attempt)
    db.flush()

    for q in quiz.questions:
        selected = answer_map.get(q.id, "")
        is_correct = selected.lower() == q.correct_answer.lower()
        if is_correct:
            correct += 1
        db.add(UserAnswer(
            attempt_id=attempt.id,
            question_id=q.id,
            selected_answer=selected,
            is_correct=is_correct
        ))

    total = len(quiz.questions)
    percentage = round((correct / total) * 100, 1) if total else 0
    attempt.score = correct
    attempt.percentage = percentage
    db.commit()
    db.refresh(attempt)

    answers = db.query(UserAnswer).filter(UserAnswer.attempt_id == attempt.id).all()
    questions = db.query(Question).filter(Question.quiz_id == quiz.id).options(joinedload(Question.topic)).all()
    return build_report(attempt, questions, answers)

@app.get("/api/dashboard")
def dashboard(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    user = get_current_user(authorization, db)
    attempts = db.query(QuizAttempt).filter(QuizAttempt.user_id == user.id).order_by(desc(QuizAttempt.created_at)).all()
    lectures = db.query(Lecture).filter(Lecture.user_id == user.id).all()

    avg = round(sum(a.percentage for a in attempts) / len(attempts), 1) if attempts else 0
    mastered = set()
    weak = set()

    for attempt in attempts:
        questions = (
            db.query(Question)
            .filter(Question.quiz_id == attempt.quiz_id)
            .options(joinedload(Question.topic))
            .all()
        )
        answers = {a.question_id: a for a in attempt.answers}
        stats = {}
        for q in questions:
            stats.setdefault(q.topic.name, [0,0])
            stats[q.topic.name][0] += 1
            if answers.get(q.id) and answers[q.id].is_correct:
                stats[q.topic.name][1] += 1
        for topic, (total, ok) in stats.items():
            pct = ok / total * 100
            if pct >= 80:
                mastered.add(topic)
            elif pct < 65:
                weak.add(topic)

    return {
        "lectures": len(lectures),
        "quizzes": len(attempts),
        "average_score": avg,
        "topics_mastered": len(mastered),
        "topics_to_revise": len(weak),
        "recent_attempts": [
            {
                "id": a.id,
                "quiz_id": a.quiz_id,
                "score": a.score,
                "percentage": a.percentage,
                "created_at": a.created_at.isoformat()
            } for a in attempts[:8]
        ]
    }

@app.get("/api/attempts/{attempt_id}/report")
def attempt_report(attempt_id: int, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    user = get_current_user(authorization, db)
    attempt = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.id == attempt_id, QuizAttempt.user_id == user.id)
        .first()
    )
    if not attempt:
        raise HTTPException(404, "Attempt not found")

    questions = (
        db.query(Question)
        .filter(Question.quiz_id == attempt.quiz_id)
        .options(joinedload(Question.topic))
        .all()
    )
    answers = db.query(UserAnswer).filter(UserAnswer.attempt_id == attempt.id).all()
    return build_report(attempt, questions, answers)

app.mount("/static", StaticFiles(directory="frontend"), name="static")
