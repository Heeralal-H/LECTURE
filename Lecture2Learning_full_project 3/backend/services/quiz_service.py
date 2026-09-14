import re
from collections import Counter

def sentences(text: str):
    text = re.sub(r"\[Page \d+\]", " ", text)
    return [
        s.strip()
        for s in re.split(r"(?<=[.!?])\s+", text)
        if 45 <= len(s.strip()) <= 300
    ]

def topic_context(topic_name: str, text: str):
    topic_words = set(re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", topic_name.lower()))
    chunks = sentences(text)
    scored = []
    for s in chunks:
        low = s.lower()
        score = sum(1 for w in topic_words if w in low)
        scored.append((score, s))
    scored.sort(reverse=True)
    return [s for score, s in scored if score > 0][:8] or chunks[:8]

def key_terms(sentence: str):
    words = re.findall(r"\b[A-Za-z][A-Za-z0-9-]{4,}\b", sentence)
    stop = {"which","these","those","there","their","about","using","between","through","because","should","where","while","other","system","process"}
    return [w for w in words if w.lower() not in stop]

def generate_questions(topic_name: str, text: str, count: int = 5):
    context = topic_context(topic_name, text)
    if not context:
        return []

    questions = []
    used = set()

    for sentence in context:
        terms = key_terms(sentence)
        if not terms:
            continue

        answer = terms[0]
        if answer.lower() in used:
            continue
        used.add(answer.lower())

        # Replace the first meaningful term with a blank.
        pattern = re.compile(re.escape(answer), re.I)
        question = pattern.sub("_____", sentence, count=1)
        if question == sentence:
            continue

        distractors = []
        all_terms = []
        for other in context:
            all_terms.extend(key_terms(other))
        for term in all_terms:
            if term.lower() != answer.lower() and term.lower() not in [d.lower() for d in distractors]:
                distractors.append(term)
            if len(distractors) >= 3:
                break

        while len(distractors) < 3:
            distractors.append(f"Concept {len(distractors)+1}")

        difficulty = "easy" if len(sentence) < 100 else ("medium" if len(sentence) < 180 else "hard")
        questions.append({
            "question_text": f"According to the lecture, complete the statement: {question}",
            "options": [answer, distractors[0], distractors[1], distractors[2]],
            "correct_answer": answer,
            "difficulty": difficulty,
            "explanation": sentence
        })

        if len(questions) >= count:
            break

    # Fallback questions if extraction cannot create blanks.
    while len(questions) < count:
        idx = len(questions) + 1
        questions.append({
            "question_text": f"Which statement best represents the main idea of {topic_name}?",
            "options": [topic_name, "An unrelated concept", "A formatting rule", "None of these"],
            "correct_answer": topic_name,
            "difficulty": "easy",
            "explanation": f"This question is associated with the topic {topic_name}."
        })

    return questions[:count]
