from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    token = Column(String(255), unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    lectures = relationship("Lecture", back_populates="user", cascade="all, delete-orphan")
    attempts = relationship("QuizAttempt", back_populates="user", cascade="all, delete-orphan")

class Lecture(Base):
    __tablename__ = "lectures"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    extracted_text = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="lectures")
    topics = relationship("Topic", back_populates="lecture", cascade="all, delete-orphan")
    quizzes = relationship("Quiz", back_populates="lecture", cascade="all, delete-orphan")

class Topic(Base):
    __tablename__ = "topics"
    id = Column(Integer, primary_key=True)
    lecture_id = Column(Integer, ForeignKey("lectures.id"), nullable=False)
    name = Column(String(255), nullable=False)
    keywords = Column(Text, default="")
    description = Column(Text, default="")

    lecture = relationship("Lecture", back_populates="topics")
    questions = relationship("Question", back_populates="topic", cascade="all, delete-orphan")

class Quiz(Base):
    __tablename__ = "quizzes"
    id = Column(Integer, primary_key=True)
    lecture_id = Column(Integer, ForeignKey("lectures.id"), nullable=False)
    title = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    lecture = relationship("Lecture", back_populates="quizzes")
    questions = relationship("Question", back_populates="quiz", cascade="all, delete-orphan")
    attempts = relationship("QuizAttempt", back_populates="quiz", cascade="all, delete-orphan")

class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    question_text = Column(Text, nullable=False)
    question_type = Column(String(30), default="mcq")
    option_a = Column(String(500))
    option_b = Column(String(500))
    option_c = Column(String(500))
    option_d = Column(String(500))
    correct_answer = Column(String(500), nullable=False)
    difficulty = Column(String(20), default="medium")
    explanation = Column(Text, default="")

    quiz = relationship("Quiz", back_populates="questions")
    topic = relationship("Topic", back_populates="questions")
    answers = relationship("UserAnswer", back_populates="question", cascade="all, delete-orphan")

class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False)
    score = Column(Float, default=0)
    percentage = Column(Float, default=0)
    time_taken = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="attempts")
    quiz = relationship("Quiz", back_populates="attempts")
    answers = relationship("UserAnswer", back_populates="attempt", cascade="all, delete-orphan")

class UserAnswer(Base):
    __tablename__ = "user_answers"
    id = Column(Integer, primary_key=True)
    attempt_id = Column(Integer, ForeignKey("quiz_attempts.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    selected_answer = Column(String(500), nullable=False)
    is_correct = Column(Boolean, default=False)

    attempt = relationship("QuizAttempt", back_populates="answers")
    question = relationship("Question", back_populates="answers")
