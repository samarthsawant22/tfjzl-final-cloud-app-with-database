
@login_required
def show_exam_result(request, course_id, submission_id):
    course = get_object_or_404(Course, pk=course_id)

    submission = get_object_or_404(
        Submission,
        pk=submission_id,
        enrollment__user=request.user,
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
        is_correct = question.is_get_score(selected_ids)

        if is_correct:
            total_score += question.grade

        question_results.append({
            "question": question,
            "choices": question.choice_set.all(),
            "selected_ids": selected_ids,
            "is_correct": is_correct,
        })

    context = {
        "course": course,
        "submission": submission,
        "questions": questions,
        "choices": submission.choices.all(),
        "selected_ids": selected_ids,
        "total_score": total_score,
        "possible_score": possible_score,
        "grade": total_score,
        "score": round(total_score / possible_score * 100)
                 if possible_score else 0,
        "question_results": question_results,
    }

    return render(
        request,
        "onlinecourse/exam_result_bootstrap.html",
        context
    )
