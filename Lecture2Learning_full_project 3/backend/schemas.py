from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional

class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6, max_length=100)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class QuizAnswer(BaseModel):
    question_id: int
    answer: str

class SubmitQuizRequest(BaseModel):
    answers: List[QuizAnswer]
    time_taken: int = Field(default=0, ge=0, le=86400)

class QuestionOut(BaseModel):
    id: int
    topic: str
    question_text: str
    question_type: str
    options: List[str]
    difficulty: str

class QuizOut(BaseModel):
    id: int
    title: str
    lecture_id: int
    questions: List[QuestionOut]

class TopicPerformance(BaseModel):
    topic: str
    total: int
    correct: int
    percentage: float
    status: str

class ReportOut(BaseModel):
    attempt_id: int
    score: float
    percentage: float
    topic_performance: List[TopicPerformance]
    strengths: List[str]
    revision_priorities: List[str]
    recommendations: List[str]
