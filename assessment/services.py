"""Business logic for the assessment flow.

Keeps question iteration, answer saving, scoring and the mapping of
assessment answers onto the user's interest/skill profile in services so
the views stay thin.
"""
from django.db import transaction
from django.utils import timezone

from assessment.models import Answer, Assessment, Question, QuestionOption, UserInterest, UserSkill


def get_active_questions() -> list[Question]:
    """All active questions ordered by their configured order."""
    return list(Question.objects.filter(is_active=True).order_by("order", "id"))


def get_question_step(question_id: int) -> int | None:
    """0-based index of a question within the active question set."""
    questions = get_active_questions()
    for idx, question in enumerate(questions):
        if question.id == question_id:
            return idx
    return None


def get_next_question(question_id: int) -> Question | None:
    questions = get_active_questions()
    for idx, question in enumerate(questions):
        if question.id == question_id and idx + 1 < len(questions):
            return questions[idx + 1]
    return None


def get_previous_question(question_id: int) -> Question | None:
    questions = get_active_questions()
    for idx, question in enumerate(questions):
        if question.id == question_id and idx > 0:
            return questions[idx - 1]
    return None


def get_or_create_assessment(user) -> Assessment:
    """Return the user's latest in-progress assessment, or start one."""
    assessment = Assessment.objects.filter(user=user, is_completed=False).first()
    if not assessment:
        assessment = Assessment.objects.create(user=user)
    return assessment


def save_answer(assessment: Assessment, question: Question, option_ids, text_answer: str = "") -> Answer:
    """Validate and persist an answer for a question."""
    score = 0
    option = None
    stored_text = text_answer.strip()[:500]

    if question.question_type in ("single_choice", "scale"):
        clean_ids = [int(x) for x in (option_ids or []) if str(x).isdigit()]
        if clean_ids:
            option = question.options.filter(pk=clean_ids[0]).first()
            score = option.score if option else 0
    elif question.question_type == "multiple_choice":
        clean_ids = [int(x) for x in (option_ids or []) if str(x).isdigit()]
        selected = question.options.filter(pk__in=clean_ids)
        score = sum(opt.score for opt in selected)
        # Preserve the full selection so revisits can re-render it.
        stored_text = ",".join(str(x) for x in clean_ids)

    answer, _ = Answer.objects.update_or_create(
        assessment=assessment,
        question=question,
        defaults={"option": option, "text_answer": stored_text, "score": score},
    )
    return answer


def is_question_answered(assessment: Assessment, question_id: int) -> bool:
    return assessment.answers.filter(question_id=question_id).exists()


def progress_data(assessment: Assessment, current_step: int | None = None) -> dict:
    """Progress-bar data: answered count vs total active questions."""
    total = len(get_active_questions())
    answered = assessment.answers.count()
    return {"answered": answered, "total": total, "percent": round(answered / total * 100) if total else 0}


@transaction.atomic
def complete_assessment(assessment: Assessment) -> Assessment:
    """Finalize an assessment: score it and sync the user's profile."""
    questions = get_active_questions()
    total_score = sum(
        (answer.score * (question.weight or 1))
        for answer in assessment.answers.select_related("question").all()
        for question in [answer.question]
        if answer.question_id in {q.id for q in questions}
    )

    assessment.score = total_score
    assessment.is_completed = True
    assessment.completed_at = timezone.now()
    assessment.save(update_fields=["score", "is_completed", "completed_at"])

    _apply_results(assessment)
    return assessment


def _apply_results(assessment: Assessment) -> None:
    """Map assessment answers onto the user's interest and skill records.

    The highest score given to each interest/skill becomes its level, which
    is exactly what the matching engine consumes. Multiple-choice answers
    store their full selection as comma-separated option ids in
    ``text_answer`` so every selected option contributes.
    """
    user = assessment.user
    answers = assessment.answers.select_related("option").only(
        "option_id", "text_answer", "score", "question__question_type"
    )

    interest_scores: dict[int, int] = {}
    skill_scores: dict[int, int] = {}

    def bump(target: dict[int, int], key: int, score: int) -> None:
        target[key] = max(target.get(key, 0), score)

    for answer in answers:
        collected = list([answer.option] if answer.option else [])
        if answer.question.question_type == "multiple_choice" and answer.text_answer:
            ids = [int(x) for x in answer.text_answer.split(",") if x.isdigit()]
            if ids:
                collected.extend(QuestionOption.objects.filter(pk__in=ids))
        for option in collected:
            if option is None:
                continue
            if option.interest_id:
                bump(interest_scores, option.interest_id, option.score)
            if option.skill_id:
                bump(skill_scores, option.skill_id, option.score)

    for interest_id, level in interest_scores.items():
        UserInterest.objects.update_or_create(
            user=user,
            interest_id=interest_id,
            defaults={"level": min(level, 5)},
        )

    for skill_id, proficiency in skill_scores.items():
        UserSkill.objects.update_or_create(
            user=user,
            skill_id=skill_id,
            defaults={"proficiency": min(proficiency, 5)},
        )