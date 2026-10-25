
import logging

from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views import generic
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from .models import (
    Course,
    Enrollment,
    Question,
    Choice,
    Submission,
)

logger = logging.getLogger(__name__)


def registration_request(request):
    context = {}

    if request.method == "GET":
        return render(
            request,
            "onlinecourse/user_registration_bootstrap.html",
            context,
        )

    username = request.POST["username"]
    password = request.POST["psw"]
    first_name = request.POST["firstname"]
    last_name = request.POST["lastname"]

    if User.objects.filter(username=username).exists():
        context["message"] = "User already exists."
        return render(
            request,
            "onlinecourse/user_registration_bootstrap.html",
            context,
        )

    user = User.objects.create_user(
        username=username,
        first_name=first_name,
        last_name=last_name,
        password=password,
    )
    login(request, user)
    return redirect("onlinecourse:index")


def login_request(request):
    context = {}

    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["psw"]
        user = authenticate(
            request,
            username=username,
            password=password,
        )

        if user is not None:
            login(request, user)
            return redirect("onlinecourse:index")

        context["message"] = "Invalid username or password."

    return render(
        request,
        "onlinecourse/user_login_bootstrap.html",
        context,
    )


def logout_request(request):
    logout(request)
    return redirect("onlinecourse:index")


def check_if_enrolled(user, course):
    if not user.is_authenticated:
        return False

    return Enrollment.objects.filter(
        user=user,
        course=course,
    ).exists()


class CourseListView(generic.ListView):
    template_name = "onlinecourse/course_list_bootstrap.html"
    context_object_name = "course_list"

    def get_queryset(self):
        courses = Course.objects.order_by("-total_enrollment")[:10]
        user = self.request.user

        for course in courses:
            course.is_enrolled = check_if_enrolled(user, course)

        return courses


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = "onlinecourse/course_details_bootstrap.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_enrolled"] = check_if_enrolled(
            self.request.user,
            self.object,
        )
        return context


def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user

    if user.is_authenticated and not check_if_enrolled(user, course):
        Enrollment.objects.create(
            user=user,
            course=course,
            mode="honor",
        )
        course.total_enrollment += 1
        course.save()

    return HttpResponseRedirect(
        reverse(
            "onlinecourse:course_details",
            args=(course.id,),
        )
    )


@login_required
def submit(request, course_id):
    course = get_object_or_404(Course, pk=course_id)

    if request.method != "POST":
        return redirect(
            "onlinecourse:course_details",
            pk=course_id,
        )

    enrollment = get_object_or_404(
        Enrollment,
        user=request.user,
        course=course,
    )

    submission = Submission.objects.create(enrollment=enrollment)
    selected_ids = extract_answers(request)

    submission.choices.set(
        Choice.objects.filter(
            question__course=course,
            id__in=selected_ids,
        )
    )

    return redirect(
        "onlinecourse:show_exam_result",
        course_id=course.id,
        submission_id=submission.id,
    )


def extract_answers(request):
    selected_ids = []

    for key in request.POST:
        if key.startswith("choice"):
            for value in request.POST.getlist(key):
                try:
                    selected_ids.append(int(value))
                except (TypeError, ValueError):
                    continue

    return selected_ids


@login_required
def show_exam_result(request, course_id, submission_id):
    course = get_object_or_404(Course, pk=course_id)

    submission = get_object_or_404(
        Submission,
        pk=submission_id,
        enrollment__user=request.user,
        enrollment__course=course,
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
            "selected_ids": selected_ids,
            "is_correct": correct,
        })

    context = {
        "course": course,
        "submission": submission,
        "questions": questions,
        "choices": submission.choices.all(),
        "selected_ids": selected_ids,
        "question_results": question_results,
        "grade": total_score,
        "total_score": total_score,
        "possible": possible_score,
        "possible_score": possible_score,
        "score": (
            round(total_score / possible_score * 100)
            if possible_score else 0
        ),
    }

    return render(
        request,
        "onlinecourse/exam_result_bootstrap.html",
        context,
    )
