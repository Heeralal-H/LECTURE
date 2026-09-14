def build_report(attempt, questions, answers):
    answer_map = {a.question_id: a for a in answers}
    stats = {}

    for q in questions:
        topic = q.topic.name
        stats.setdefault(topic, {"total": 0, "correct": 0})
        stats[topic]["total"] += 1
        if answer_map.get(q.id) and answer_map[q.id].is_correct:
            stats[topic]["correct"] += 1

    performance = []
    strengths = []
    revision = []

    for topic, value in stats.items():
        pct = round((value["correct"] / value["total"]) * 100, 1)
        status = "Strong" if pct >= 80 else ("Good" if pct >= 65 else "Needs Revision")
        performance.append({
            "topic": topic,
            "total": value["total"],
            "correct": value["correct"],
            "percentage": pct,
            "status": status
        })
        if pct >= 80:
            strengths.append(topic)
        elif pct < 65:
            revision.append(topic)

    revision.sort(key=lambda t: stats[t]["correct"] / max(stats[t]["total"], 1))

    recommendations = []
    for topic in revision:
        recommendations.append(
            f"Revise {topic}, then attempt another practice quiz focused on this topic."
        )
    if not recommendations:
        recommendations.append("Great performance. Try a harder quiz to reinforce your understanding.")

    return {
        "attempt_id": attempt.id,
        "score": attempt.score,
        "percentage": attempt.percentage,
        "topic_performance": performance,
        "strengths": strengths,
        "revision_priorities": revision,
        "recommendations": recommendations
    }
