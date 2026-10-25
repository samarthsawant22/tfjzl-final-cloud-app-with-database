from .models import Course, Enrollment, Question, Choice, Submission
from django.contrib.auth.decorators import login_required
from django.db.models import Sum

@login_required
def submit(request, course_id):
    course = get_object_or_404(Course, pk=course_id)

    if request.method != "POST":
        return redirect("onlinecourse:course_details", pk=course_id)

    enrollment = get_object_or_404(
        Enrollment, user=request.user, course=course
    )

    submission = Submission.objects.create(enrollment=enrollment)
    selected_ids = extract_answers(request)
    submission.choices.set(
        Choice.objects.filter(
            question__course=course, id__in=selected_ids
        )
    )

    return redirect(
        "onlinecourse:show_exam_result",
        course_id=course.id,
        submission_id=submission.id
    )


def extract_answers(request):
    selected_ids = []
    for key, value in request.POST.items():
        if key.startswith("choice"):
            try:
                selected_ids.append(int(value))
            except (TypeError, ValueError):
                continue
    return selected_ids


@login_required
def show_exam_result(request, course_id, submission_id):
    course = get_object_or_404(Course, pk=course_id)
    submission = get_object_or_404(
        Submission, pk=submission_id, enrollment__user=request.user,
        enrollment__course=course
    )

    selected_ids = list(
        submission.choices.values_list("id", flat=True)
    )
    questions = course.question_set.prefetch_related("choice_set")
    total_score = 0
    possible_score = 0
    question_results = []

    for question in questions:
        possible_score += question.grade
        correct = question.is_get_score(selected_ids)

        if correct:
            total_score += question.grade

        question_results.append({
            "question": question,
            "choices": question.choice_set.all(),
            "selected_choices": question.choice_set.filter(
                id__in=selected_ids
            ),
            "is_correct": correct,
        })

    context = {
        "course": course,
        "submission": submission,
        "questions": questions,
        "choices": submission.choices.all(),
        "question_results": question_results,
        "grade": total_score,
        "total_score": total_score,
        "possible_score": possible_score,
        "score": (
            round(total_score / possible_score * 100)
            if possible_score else 0
        ),
    }

    return render(
        request, "onlinecourse/exam_result_bootstrap.html", context
    )
