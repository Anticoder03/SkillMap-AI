"""Views for the multi-step assessment flow."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from recommendations.services.matcher import generate_recommendations

from .models import Assessment, Question
from .services import (
    complete_assessment,
    get_active_questions,
    get_next_question,
    get_or_create_assessment,
    get_previous_question,
    get_question_step,
    progress_data,
    save_answer,
)


@login_required
def start(request):
    """Begin (or resume) an assessment and jump to the first open question."""
    assessment = get_or_create_assessment(request.user)
    first_question = get_next_question(0) or get_active_questions()[0]
    return redirect("assessment:question", question_id=first_question.id)


@login_required
def question(request, question_id: int):
    """Render a single assessment question step with prev/next navigation."""
    assessment = get_or_create_assessment(request.user)
    question_obj = get_object_or_404(Question, pk=question_id, is_active=True)

    if request.method == "POST":
        option_ids = request.POST.getlist("option")
        text_answer = request.POST.get("text_answer", "")
        save_answer(assessment, question_obj, option_ids, text_answer)

        action = request.POST.get("action", "next")
        if action == "previous":
            previous = get_previous_question(question_obj.id)
            if previous:
                return redirect("assessment:question", question_id=previous.id)

        next_question = get_next_question(question_obj.id)
        if next_question:
            return redirect("assessment:question", question_id=next_question.id)

        # No more questions: finalize the assessment.
        complete_assessment(assessment)
        generate_recommendations(request.user)
        messages.success(request, "Assessment complete! Here are your career matches.")
        return redirect("recommendations:list")

    step = get_question_step(question_obj.id) or 0
    existing_answer = assessment.answers.filter(question=question_obj).first()
    answered_option_ids = []
    answered_text = existing_answer.text_answer if existing_answer else ""
    if existing_answer:
        if question_obj.question_type == "multiple_choice":
            answered_option_ids = [
                int(x) for x in answered_text.split(",") if x.strip().isdigit()
            ]
        elif question_obj.question_type in ("single_choice", "scale") and existing_answer.option_id:
            answered_option_ids = [existing_answer.option_id]

    context = {
        "assessment": assessment,
        "question": question_obj,
        "step": step,
        "total_questions": len(get_active_questions()),
        "answered": bool(existing_answer),
        "answered_option_id": answered_option_ids[0] if len(answered_option_ids) == 1 else None,
        "answered_option_ids": answered_option_ids,
        "answered_text": answered_text if question_obj.question_type == "text" else "",
        "progress": progress_data(assessment),
        "has_previous": bool(get_previous_question(question_obj.id)),
    }
    return render(request, "assessment/question.html", context)


@login_required
def complete(request, assessment_id: int):
    """Manually finalize an assessment and jump to recommendations."""
    assessment = get_object_or_404(Assessment, pk=assessment_id, user=request.user)
    complete_assessment(assessment)
    generate_recommendations(request.user)
    messages.success(request, "Assessment complete! Your recommendations are ready.")
    return redirect("recommendations:list")