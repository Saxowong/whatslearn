from django.db.models import FloatField
from django.shortcuts import render, get_object_or_404, redirect
from rest_framework import generics, permissions
from django.db.models import Prefetch
from django.contrib import messages
from django.db import IntegrityError, transaction
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from datetime import timedelta, datetime
from zoneinfo import ZoneInfo
from django.urls import reverse
from django.utils import timezone
import json
from random import shuffle, sample
import logging

from django.db.models import (
    OuterRef,
    Subquery,
    F,
    Case,
    BooleanField,
    FloatField,
    IntegerField,
    Value,
    When,
    ExpressionWrapper,
    Count,
)
from django.db.models.functions import Coalesce
from .models import (
    Course,
    Lesson,
    Activity,
    StudentActivity,
    StudentItem,
    StudentCourse,
)

logger = logging.getLogger(__name__)


from .models import (
    Course,
    Activity,
    Item,
    Profile,
    StudentCourse,
    StudentActivity,
    StudentItem,
    GroupConcat,
)

from .serializers import (
    CourseSerializer,
    CourseWithLessonsSerializer,
    ProfileSerializer,
    CourseProgressSerializer,
)

# Create your views here.


# Endpoint 1: List all courses
class CourseListView(generics.ListAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer


# Endpoint 2: List lessons (with activities) for a specific course
class CourseLessonsView(generics.ListAPIView):
    queryset = Course.objects.prefetch_related("lessons").all()
    serializer_class = CourseWithLessonsSerializer
    lookup_field = "course_id"  # Use course_id as the lookup field


class UserProfileAPIView(generics.RetrieveAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        # Get profile for the currently authenticated user
        return self.request.user.profile


class ProfileByUserIDAPIView(generics.RetrieveAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAdminUser]  # Restrict to admin

    def get_object(self):
        user_id = self.kwargs["user_id"]
        return Profile.objects.get(user__id=user_id)


class UserEnrolledCoursesAPIView(generics.ListAPIView):
    serializer_class = CourseProgressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Get all courses where the current user is enrolled"""
        student = self.request.user.profile
        enrolled_courses = (
            StudentCourse.objects.filter(student=student)
            .select_related("course")
            .prefetch_related("course__lessons__activities")
        )
        return [sc.course for sc in enrolled_courses]

    def get_serializer_context(self):
        """Pass the request object to serializer"""
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


@login_required
def student_course_view(request):
    user = request.user.profile

    first_course_activity_subquery = (
        Activity.objects.filter(lesson__course=OuterRef("course"))
        .order_by("id")
        .values("id")[:1]
    )

    latest_student_activity_subquery = (
        StudentActivity.objects.filter(
            student=user, activity__lesson__course=OuterRef("course")
        )
        .order_by("-updated_at")
        .values("activity_id")[:1]
    )

    first_student_activity_subquery = (
        StudentActivity.objects.filter(
            student=user, activity__lesson__course=OuterRef("course")
        )
        .order_by("updated_at")
        .values("activity_id")[:1]
    )

    enrollments = (
        StudentCourse.objects.filter(student=user)
        .select_related("course")
        .annotate(
            total_activities=Subquery(
                Activity.objects.filter(lesson__course=OuterRef("course"))
                .values("lesson__course")
                .annotate(count=Count("pk"))
                .values("count")[:1],
                output_field=FloatField(),
            ),
            completed_activities=Coalesce(
                Subquery(
                    StudentActivity.objects.filter(
                        student=user,
                        activity__lesson__course=OuterRef("course"),
                        completed=True,
                    )
                    .values("activity__lesson__course")
                    .annotate(count=Count("pk"))
                    .values("count")[:1],
                    output_field=FloatField(),
                ),
                0.0,
            ),
            progress=Coalesce(
                ExpressionWrapper(
                    (F("completed_activities") / F("total_activities")) * 100,
                    output_field=FloatField(),
                ),
                0.0,
                output_field=FloatField(),
            ),
            revision_items_count=Coalesce(
                Subquery(
                    StudentItem.objects.filter(
                        student=user,
                        item__activity__lesson__course=OuterRef("course_id"),
                        revise_at__lte=timezone.now(),
                        continue_revision=True,
                    )
                    .values("student")
                    .annotate(count=Count("id"))
                    .values("count")[:1],
                    output_field=FloatField(),
                ),
                0.0,
            ),
            latest_activity_id=Coalesce(
                Subquery(latest_student_activity_subquery, output_field=IntegerField()),
                Subquery(first_course_activity_subquery, output_field=IntegerField()),
                output_field=IntegerField(),
            ),
            first_activity_id=Coalesce(
                Subquery(first_student_activity_subquery, output_field=IntegerField()),
                Subquery(first_course_activity_subquery, output_field=IntegerField()),
                output_field=IntegerField(),
            ),
        )
        .order_by("-updated_at")
    )

    context = {"enrollments": enrollments}
    return render(request, "course/courses.html", context)


@login_required
def available_courses_view(request):
    # Get the student's profile
    user = request.user.profile

    # Get all courses NOT enrolled by the user and are published
    unenrolled_courses = (
        Course.objects.exclude(
            id__in=StudentCourse.objects.filter(student=user).values("course_id")
        )
        .filter(is_published=True)
        .order_by("-created_at")
    )  # Order by newest first

    context = {"courses": unenrolled_courses}
    return render(request, "course/available_courses.html", context)


@login_required
def revision_view(request, course_id):
    user = request.user.profile
    # Get the specific course
    course = get_object_or_404(
        Course.objects.filter(
            id__in=StudentCourse.objects.filter(student=user).values("course_id")
        )
        .annotate(
            revision_items_count=Subquery(
                StudentItem.objects.filter(
                    student=user,
                    item__activity__lesson__course=OuterRef("pk"),
                    revise_at__lte=timezone.now(),
                    continue_revision=True,
                )
                .values("student")
                .annotate(count=Count("id"))
                .values("count")[:1]
            )
        )
        .select_related("teacher__user"),
        id=course_id,
    )
    # Get all enrolled courses for navigation, sorted by revision_items_count (descending)
    revision_courses = (
        Course.objects.filter(
            id__in=StudentCourse.objects.filter(student=user).values("course_id")
        )
        .annotate(
            revision_items_count=Subquery(
                StudentItem.objects.filter(
                    student=user,
                    item__activity__lesson__course=OuterRef("pk"),
                    revise_at__lte=timezone.now(),
                    continue_revision=True,
                )
                .values("student")
                .annotate(count=Count("id"))
                .values("count")[:1]
            )
        )
        .select_related("teacher__user")
        .order_by(Coalesce("revision_items_count", 0).desc(), "title")
    )
    # Get items due for revision first
    due_items = (
        StudentItem.objects.filter(
            student=user,
            item__activity__lesson__course=course,
            revise_at__lte=timezone.now(),
            continue_revision=True,
        )
        .select_related("item__activity")
        .values(
            "id",
            "item__id",
            "item__title",
            "item__item_type",
            "item__question",
            "item__hint",
            "item__answer",
            "item__answer1",
            "item__answer2",
            "item__answer3",
            "item__answer4",
            "item__number_answers",
            "item__image",
            "item__audio",
            "item__audio_play",
            "item__activity_id",
            "successes",
            "is_master",
            "next_1",
            "next_2",
            "revise_at",
            "continue_revision",
        )
        .order_by("revise_at")
    )
    # If less than 10 due items, get additional items with fewest successes
    items = list(due_items)
    if len(items) < 10:
        remaining_count = 10 - len(items)
        additional_items = (
            StudentItem.objects.filter(
                student=user,
                item__activity__lesson__course=course,
                continue_revision=True,
            )
            .exclude(id__in=[item["id"] for item in items])
            .select_related("item__activity")
            .values(
                "id",
                "item__id",
                "item__title",
                "item__item_type",
                "item__question",
                "item__hint",
                "item__answer",
                "item__answer1",
                "item__answer2",
                "item__answer3",
                "item__answer4",
                "item__number_answers",
                "item__image",
                "item__audio",
                "item__audio_play",
                "item__activity_id",
                "successes",
                "is_master",
                "next_1",
                "next_2",
                "revise_at",
                "continue_revision",
            )
            .order_by("successes", "id")[:remaining_count]
        )
        items.extend(additional_items)

    course.revision_items = []
    for item in items:
        # Collect answer options
        options = []
        correct_answer = None
        correct_sequence = []
        if item["item__item_type"] == "blank":
            # Only include non-empty answers from answer1 to answer4
            answers = [
                ans
                for ans in [
                    item["item__answer1"],
                    item["item__answer2"],
                    item["item__answer3"],
                    item["item__answer4"],
                ]
                if ans and ans.strip()
            ]
            options = answers
            correct_answer = item["item__answer1"] or ""  # Fallback for blank items
            correct_sequence = answers  # Sequence for fill-in-the-blank
            shuffle(options)
        elif item["item__item_type"] == "card":
            # For flash cards, include the correct answer plus distractors from the same activity
            activity_id = item["item__activity_id"]
            wrong_answers = (
                Item.objects.filter(activity_id=activity_id, item_type="card")
                .exclude(id=item["item__id"])
                .exclude(answer__isnull=True)
                .values_list("answer", flat=True)
                .distinct()
            )
            wrong_answers = list(wrong_answers)
            wrong_answers = (
                wrong_answers[:3]
                if len(wrong_answers) >= 3
                else wrong_answers
                + ["Option " + str(i) for i in range(1, 4 - len(wrong_answers) + 1)]
            )
            options = [item["item__answer"]] + wrong_answers
            correct_answer = item["item__answer"] or ""
            correct_sequence = [correct_answer]
            shuffle(options)
        elif item["item__item_type"] == "mc":
            # For multiple-choice, include answer1 to answer4
            answers = [
                ans
                for ans in [
                    item["item__answer1"],
                    item["item__answer2"],
                    item["item__answer3"],
                    item["item__answer4"],
                ]
                if ans and ans.strip()
            ]
            options = answers
            correct_answer = (
                item["item__answer"] or ""
            )  # Use item__answer as the correct answer
            correct_sequence = [correct_answer]
            shuffle(options)

        item_data = {
            "id": item["id"],
            "item_id": item["item__id"],
            "item_type": item["item__item_type"],
            "title": item["item__title"],
            "hint": item["item__hint"],
            "question": item["item__question"],
            "answer": item["item__answer"],
            "answer1": item["item__answer1"],
            "answer2": item["item__answer2"],
            "answer3": item["item__answer3"],
            "answer4": item["item__answer4"],
            "number_answers": item["item__number_answers"] or 1,
            "audio_play": item["item__audio_play"],
            "successes": item["successes"],
            "is_master": item["is_master"],
            "next_1": item["next_1"],
            "next_2": item["next_2"],
            "revise_at": (item["revise_at"].isoformat() if item["revise_at"] else None),
            "continue_revision": item["continue_revision"],
            "options": options,
            "correct_answer": correct_answer,
            "correct_sequence_json": json.dumps(correct_sequence),
        }
        # Handle image and audio files
        if item["item__image"]:
            try:
                item_data["image"] = Item.objects.get(id=item["item__id"]).image.url
            except (Item.DoesNotExist, ValueError):
                item_data["image"] = None
        if item["item__audio"]:
            try:
                item_data["audio"] = Item.objects.get(id=item["item__id"]).audio.url
            except (Item.DoesNotExist, ValueError):
                item_data["audio"] = None
        course.revision_items.append(item_data)

    context = {
        "courses": revision_courses,
        "first_course": course,
    }
    return render(request, "course/revision.html", context)


@login_required
@require_POST
def submit_revision(request, course_id):
    user = request.user.profile

    try:
        # Verify course access
        course = get_object_or_404(
            Course,
            id=course_id,
            id__in=StudentCourse.objects.filter(student=user).values("course__id"),
        )

        # Parse form data
        responses = json.loads(request.POST.get("responses", "[]"))
        is_completed = request.POST.get("is_completed", "false").lower() == "true"

        # Log incoming data

        logger.debug(f"Received responses: {responses}")  # Add this line

        # Validate and update items
        for response in responses:
            try:
                student_item_id = int(response.get("student_item_id"))
                successes = int(response.get("successes", 0))
                next_1 = int(response.get("next_1", 1))
                next_2 = int(response.get("next_2", 1))
                revise_at = response.get("revise_at")
                continue_revision = bool(response.get("continue_revision", True))
                logger.debug(
                    f"Processing item {response.get('student_item_id')} - continue_revision: {continue_revision}"
                )
                # Validate required fields
                if not all([student_item_id, revise_at]):
                    logger.error(f"Missing required fields in response: {response}")
                    return JsonResponse(
                        {
                            "status": "error",
                            "message": "Missing required fields in response",
                        },
                        status=400,
                    )

                # Parse revise_at as datetime
                try:
                    revise_at_dt = datetime.fromisoformat(
                        revise_at.replace("Z", "+00:00")
                    )
                except ValueError as e:
                    logger.error(
                        f"Invalid revise_at format in response {response}: {str(e)}"
                    )
                    return JsonResponse(
                        {
                            "status": "error",
                            "message": f"Invalid revise_at format: {str(e)}",
                        },
                        status=400,
                    )

                # Update StudentItem
                item = StudentItem.objects.get(
                    id=student_item_id,
                    student=user,
                    item__activity__lesson__course=course,  # Fixed typo
                )
                item.successes = successes
                item.next_1 = next_1
                item.next_2 = next_2
                item.revise_at = revise_at_dt
                item.is_master = successes >= 3
                item.continue_revision = continue_revision
                item.save()

                logger.debug(
                    f"Updated StudentItem {student_item_id}: successes={successes}, next_1={next_1}, next_2={next_2}, revise_at={revise_at_dt}"
                )

            except StudentItem.DoesNotExist:
                logger.error(
                    f"StudentItem {student_item_id} not found for user {user.user.username}, course {course_id}"
                )
                return JsonResponse(
                    {
                        "status": "error",
                        "message": f"StudentItem {student_item_id} not found",
                    },
                    status=400,
                )
            except ValueError as e:
                logger.error(f"Invalid data in response {response}: {str(e)}")
                return JsonResponse(
                    {"status": "error", "message": f"Invalid data: {str(e)}"},
                    status=400,
                )

        # Calculate remaining items
        remaining_items = StudentItem.objects.filter(
            student=user,
            item__activity__lesson__course=course,
            revise_at__lte=timezone.now(),
            continue_revision=True,
        ).count()

        # Prepare redirect URL
        redirect_url = reverse("revision", kwargs={"course_id": course_id})

        logger.info(
            f"submit_revision: Successfully saved {len(responses)} items for course {course_id}, remaining_items={remaining_items}"
        )

        return JsonResponse(
            {
                "status": "success",
                "message": "Revision progress saved successfully",
                "stats": {"remaining_items": remaining_items},
                "redirect_url": redirect_url,
            }
        )

    except json.JSONDecodeError as e:
        logger.error(
            f"Invalid JSON in responses: {request.POST.get('responses')}, error: {str(e)}"
        )
        return JsonResponse(
            {"status": "error", "message": "Invalid JSON in responses"}, status=400
        )
    except Exception as e:
        logger.error(
            f"Unexpected error in submit_revision for course {course_id}, user {user.user.username}: {str(e)}"
        )
        return JsonResponse(
            {"status": "error", "message": f"An unexpected error occurred: {str(e)}"},
            status=500,
        )


@login_required
def course_view(request, course_id):
    student_profile = request.user.profile
    course = get_object_or_404(
        Course.objects.prefetch_related(
            Prefetch(
                "lessons",
                queryset=Lesson.objects.prefetch_related(
                    Prefetch(
                        "activities",
                        queryset=Activity.objects.annotate(
                            # -------------------------- MODIFICATION 1: Remove On-The-Fly Progress Calculations (Keep Nothing Related to total_items/mastered_items) --------------------------
                            # DELETED: total_items=Count("items")
                            # DELETED: mastered_items=Coalesce(...)
                            # -------------------------- MODIFICATION 2: Retrieve Stored StudentActivity.progress (Replace On-The-Fly student_progress) --------------------------
                            student_progress=Coalesce(
                                Subquery(
                                    StudentActivity.objects.filter(
                                        activity=OuterRef(
                                            "pk"
                                        ),  # Link to current Activity
                                        student=student_profile,  # Link to current student
                                    ).values("progress")[
                                        :1
                                    ],  # Fetch stored progress value from StudentActivity
                                    output_field=FloatField(),
                                ),
                                0.0,  # Default to 0% if no StudentActivity record exists
                                output_field=FloatField(),
                            ),
                            # -------------------------- UNCHANGED: student_completed (Already Fetches Stored StudentActivity Value) --------------------------
                            student_completed=Coalesce(
                                Subquery(
                                    StudentActivity.objects.filter(
                                        activity=OuterRef("pk"), student=student_profile
                                    ).values("completed")[:1],
                                    output_field=BooleanField(),
                                ),
                                False,
                                output_field=BooleanField(),
                            ),
                        ).order_by("order"),
                    )
                ).order_by("order"),
            )
        ).annotate(
            # -------------------------- UNCHANGED: All Course-Level Annotations --------------------------
            revision_items_count=Subquery(
                StudentItem.objects.filter(
                    student=student_profile,
                    item__activity__lesson__course=OuterRef("pk"),
                    revise_at__lte=timezone.now(),
                )
                .values("student")
                .annotate(count=Count("id"))
                .values("count")[:1],
                output_field=IntegerField(),
            ),
            activities_completed=Subquery(
                StudentActivity.objects.filter(
                    student=student_profile,
                    activity__lesson__course=OuterRef("pk"),
                    completed=True,
                )
                .values("student")
                .annotate(count=Count("id"))
                .values("count")[:1],
                output_field=IntegerField(),
            ),
        ),
        id=course_id,
    )
    # -------------------------- UNCHANGED: Category Progress (Exact Original Logic) --------------------------
    category_progress = (
        StudentItem.objects.filter(
            student=student_profile,
            item__activity__lesson__course=course,
            successes__gte=3,
        )
        .values("item__item_category")
        .annotate(mastered_count=Count("id"))
        .order_by("item__item_category")
    )
    # -------------------------- UNCHANGED: Continuous Activity Numbering --------------------------
    activity_counter = 1
    for lesson in course.lessons.all():
        for activity in lesson.activities.all():
            activity.global_index = activity_counter
            activity_counter += 1
    # -------------------------- UNCHANGED: Update StudentCourse Timestamp --------------------------
    try:
        enrollment = StudentCourse.objects.get(student=student_profile, course=course)
        enrollment.save()  # auto_now=True updates timestamp
    except StudentCourse.DoesNotExist:
        pass
    return render(
        request,
        "course/course.html",
        {
            "course": course,
            "student_profile": student_profile,
            "category_progress": category_progress,
        },
    )


@login_required
def activity_view(request, activity_id):
    from random import shuffle
    from django.utils import timezone
    import json

    activity = get_object_or_404(
        Activity.objects.select_related("lesson__course"), pk=activity_id
    )
    lesson = activity.lesson
    course = lesson.course

    if not StudentCourse.objects.filter(
        student=request.user.profile, course=course
    ).exists():
        raise PermissionDenied("You are not enrolled in this course")

    # Navigation: all activities in course
    all_activities = (
        Activity.objects.filter(lesson__course=course)
        .select_related("lesson")
        .annotate(
            student_progress=Coalesce(
                Subquery(
                    StudentActivity.objects.filter(
                        activity=OuterRef("pk"), student=request.user.profile
                    ).values("progress")[:1]
                ),
                0.0,
                output_field=FloatField(),
            ),
            student_completed=Coalesce(
                Subquery(
                    StudentActivity.objects.filter(
                        activity=OuterRef("pk"), student=request.user.profile
                    ).values("completed")[:1]
                ),
                False,
                output_field=BooleanField(),
            ),
        )
        .order_by("lesson__order", "order")
    )

    counter = 1
    for a in all_activities:
        a.global_index = counter
        counter += 1

    previous_activity = None
    next_activity = None
    all_activities_list = list(all_activities)
    for i, a in enumerate(all_activities_list):
        if a.id == activity.id:
            if i > 0:
                previous_activity = all_activities_list[i - 1]
            if i < len(all_activities_list) - 1:
                next_activity = all_activities_list[i + 1]
            break

    lesson_activities = [a for a in all_activities if a.lesson_id == lesson.id]

    student_activity, created = StudentActivity.objects.get_or_create(
        student=request.user.profile,
        activity=activity,
        defaults={"progress": 0.0, "completed": False},
    )

    context = {
        "activity": activity,
        "student_activity": student_activity,
        "is_enrolled": True,
        "course_id": course.id,
        "activities": lesson_activities,
        "previous_activity": previous_activity,
        "next_activity": next_activity,
    }

    if activity.activity_type == "exercise":
        # Get ALL items
        all_items = list(activity.items.all())

        # StudentItem data
        student_items_qs = StudentItem.objects.filter(
            student=request.user.profile, item__in=all_items
        )
        student_items_dict = {si.item_id: si for si in student_items_qs}

        # Separate active vs skipped + attach attributes
        active_items = []
        skipped_items = []
        for item in all_items:
            si = student_items_dict.get(item.id)
            item.successes = si.successes if si else 0
            item.is_master = si.is_master if si else False
            item.continue_revision = si.continue_revision if si else True
            item.revise_at = si.revise_at if si else None
            item.next_1 = si.next_1 if si else 1
            item.next_2 = si.next_2 if si else 1
            item.audio_play = getattr(item, "audio_play", "start")

            # Audio URL logic
            if not item.audio and item.title:
                from django.utils.html import strip_tags

                text = strip_tags(item.title).strip().lower()
                first_word = text.split()[0] if text else ""
                item.audio_url = (
                    f"/media/mp3/{first_word[0]}/{first_word}.mp3" if first_word else ""
                )
            else:
                item.audio_url = item.audio.url if item.audio else ""

            if item.continue_revision:
                active_items.append(item)
            else:
                skipped_items.append(item)

        # ======================
        # NEW: SORT ACTIVE ITEMS BY YOUR PRIORITY RULES
        # Priority 1: Started but not mastered (successes 1 or 2)
        # Priority 2: Not started (successes 0)
        # Priority 3: Mastered (successes >=3 or is_master=True)
        # ======================
        def get_priority_key(item):
            # Define priority tiers (lower number = higher priority)
            if 1 <= item.successes <= 2:
                return 0  # Highest priority (started but not mastered)
            elif item.successes == 0:
                return 1  # Second priority (not started)
            else:
                return 2  # Lowest priority (mastered)

        # Sort active items by priority tier, then by successes (ascending)
        active_items_sorted = sorted(
            active_items,
            key=lambda x: (
                get_priority_key(x),  # Main priority tier
                x.successes,  # Within tier: fewer successes first
            ),
        )

        # Select up to 10 from sorted active items
        selected_items = active_items_sorted[:10]

        # If still need more items (active items < 10), add from skipped items
        if len(selected_items) < 10:
            needed = 10 - len(selected_items)
            # Shuffle skipped items to avoid bias when adding
            shuffle(skipped_items)
            selected_items.extend(skipped_items[:needed])

        # Optional: Shuffle selected items to avoid predictable order (keeps priority logic intact)
        shuffle(selected_items)

        # ======================
        # END NEW PRIORITY LOGIC
        # ======================

        # Shuffle and prepare options for selected items
        for item in selected_items:
            if item.item_type == "mc":
                options = [getattr(item, f"answer{i}", "") for i in range(1, 5)]
                options = [o.strip() for o in options if o.strip()]
                shuffle(options)
                item.options = options
                item.correct_answer = item.answer or ""
                item.correct_sequence_json = json.dumps([])
                item.number_answers = 0

            elif item.item_type == "blank":
                blanks = item.number_answers or 0
                if not (1 <= blanks <= 4):
                    item.options = []
                    item.correct_sequence_json = json.dumps([])
                    item.number_answers = 0
                    continue
                correct_seq = [
                    getattr(item, f"answer{i}", "").strip()
                    for i in range(1, blanks + 1)
                    if getattr(item, f"answer{i}", "").strip()
                ]
                distractors = [
                    getattr(item, f"answer{i}", "").strip()
                    for i in range(blanks + 1, 5)
                    if getattr(item, f"answer{i}", "").strip()
                ]
                options = correct_seq[:]
                needed = max(0, 4 - len(options))
                if len(distractors) < needed:
                    distractors.extend(
                        [
                            f"Option {i}"
                            for i in range(1, needed + 1 - len(distractors) + 1)
                        ]
                    )
                options.extend(distractors[:needed])
                shuffle(options)
                item.options = options
                item.correct_sequence = correct_seq
                item.correct_sequence_json = json.dumps(correct_seq)
                item.number_answers = blanks

            else:  # card type
                wrong = [
                    i.answer
                    for i in all_items
                    if i.id != item.id and i.answer and i.answer != item.answer
                ]
                if len(wrong) < 3:
                    wrong.extend(
                        ["Alternative 1", "Alternative 2", "Alternative 3"][
                            : 3 - len(wrong)
                        ]
                    )
                wrongs = wrong[:3]
                shuffle(wrongs)
                options = [item.answer or ""] + wrongs
                shuffle(options)
                item.options = options
                item.correct_answer = item.answer or ""
                item.correct_sequence_json = json.dumps([])
                item.number_answers = 0

        # === OVERALL MASTERY FOR WELCOME BLOCK (includes skipped) ===
        total_items_all = len(all_items)
        mastered_total = sum(
            1
            for item in all_items
            if student_items_dict.get(item.id) and student_items_dict[item.id].is_master
        )

        # Calculate progress (mastered items / total items) * 100
        progress = (
            (mastered_total / total_items_all) * 100 if total_items_all > 0 else 100
        )
        student_activity.progress = progress
        student_activity.completed = progress >= 100  # Completed when 100% mastered
        student_activity.updated_at = timezone.now()
        student_activity.save()

        # Pass to template
        context.update(
            {
                "items": selected_items,
                "mastered_items_count": mastered_total,
                "total_items": total_items_all,
            }
        )
        template_name = "course/exercise_activity.html"

    elif activity.activity_type == "video":
        template_name = "course/video_activity.html"
    elif activity.activity_type == "pdf":
        template_name = "course/pdf_activity.html"
    else:
        template_name = "course/html_activity.html"

    return render(request, template_name, context)


def update_revision(request):
    """AJAX endpoint to set StudentItem.continue_revision=False (preserve all other fields)."""
    try:
        import json

        data = json.loads(request.body)
        item_id = data.get("item_id")

        if not item_id:
            return JsonResponse({"success": False, "error": "Item ID is required."})

        # Get current student's profile
        try:
            current_student_profile = request.user.profile
        except Profile.DoesNotExist:
            return JsonResponse(
                {"success": False, "error": "Student profile not found."}
            )

        # ---------- Critical Fix for Issue 2: Preserve all other fields ----------
        # Option 1: Update EXISTING StudentItem record (if it exists)
        try:
            student_item = StudentItem.objects.get(
                student=current_student_profile, item_id=item_id
            )

            # ONLY update the continue_revision field (leave all others untouched)
            student_item.continue_revision = False
            # updated_at is auto-set via model's auto_now=True, so no need to manually update
            student_item.save()

        # Option 2: Create NEW StudentItem record (only if no existing record)
        # Use model defaults for all fields EXCEPT continue_revision=False
        except StudentItem.DoesNotExist:
            StudentItem.objects.create(
                student=current_student_profile,
                item_id=item_id,
                continue_revision=False,  # Explicitly set only this field
                # All other fields use StudentItem model defaults (no need to specify)
                # successes=0, is_master=False, next_1=1, next_2=1, etc.
            )

        # Return success response
        return JsonResponse({"success": True})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


# Add @login_required to ensure we have a logged-in user (required for student progress)
@login_required
def view_items(request, activity_id):
    # 1. Fetch the Activity object (404 if not found)
    activity = get_object_or_404(Activity, id=activity_id)

    # 2. Fetch the related Lesson (to get all activities in the lesson)
    lesson = activity.lesson

    # 3. Fetch ALL activities for the lesson (sorted by order)
    activities = Activity.objects.filter(lesson=lesson).order_by("order")

    # 4. Attach student-specific progress data via StudentActivity
    try:
        current_student_profile = request.user.profile
    except Profile.DoesNotExist:
        current_student_profile = None
        student_activity_records = []
    else:
        student_activity_records = StudentActivity.objects.filter(
            student=current_student_profile,
            activity__in=activities,
        ).select_related("activity")

    # 4.3: StudentActivity lookup dictionary
    student_activity_lookup = {
        record.activity.id: record for record in student_activity_records
    }

    # 4.4: Attach template-required attributes to each Activity
    for a in activities:
        activity_record = student_activity_lookup.get(a.id)
        if a.activity_type == "exercise":
            a.student_progress = (
                round(activity_record.progress, 0)
                if (activity_record and activity_record.progress is not None)
                else 0
            )
        else:
            a.student_completed = (
                activity_record.completed if activity_record else False
            )

    # 5. Previous/next activity logic (unchanged)
    activity_list = list(activities)
    current_index = activity_list.index(activity) if activity in activity_list else 0
    previous_activity = activity_list[current_index - 1] if current_index > 0 else None
    next_activity = (
        activity_list[current_index + 1]
        if current_index < len(activity_list) - 1
        else None
    )

    # 6. Fetch ALL related Item objects for the activity (sorted by order)
    all_items = Item.objects.filter(activity=activity).order_by("order")

    # 7. Critical Fix: Fetch EXISTING StudentItem records (preserve all fields)
    student_item_lookup = {}
    if current_student_profile:
        # Fetch ALL StudentItem records for the current student and this activity's items
        # This preserves ALL fields (successes, is_master, etc.) from the database
        student_item_records = StudentItem.objects.filter(
            student=current_student_profile, item__in=all_items
        ).select_related("item")

        # Convert to lookup dictionary (item_id -> full StudentItem record)
        student_item_lookup = {
            record.item.id: record for record in student_item_records
        }

    # 8. Process items: Attach StudentItem data & FILTER ONLY continue_revision=True
    processed_items = []
    visible_item_index = 1  # Only increment for visible items (no gaps in numbering)

    for item in all_items:
        # Get the EXISTING StudentItem record (if it exists)
        student_item_record = student_item_lookup.get(item.id)

        # ---------- Critical Fix for Issue 1: Strict continue_revision logic ----------
        # Priority 1: Use existing StudentItem's continue_revision (if record exists)
        # Priority 2: Default to True ONLY if NO StudentItem record exists
        if student_item_record:
            item.continue_revision = student_item_record.continue_revision
            # Optional: Attach other StudentItem fields to the item (for template use if needed)
            item.successes = student_item_record.successes
            item.is_master = student_item_record.is_master
            item.next_1 = student_item_record.next_1
            item.next_2 = student_item_record.next_2
        else:
            item.continue_revision = (
                True  # Default only for new items (no existing record)
            )
            # Attach model defaults for other fields (matching StudentItem model)
            item.successes = 0
            item.is_master = False
            item.next_1 = 1
            item.next_2 = 1

        # ---------- Only add items with continue_revision=True to processed_items ----------
        if item.continue_revision:
            # Set item number (only for visible items)
            item.item_number = visible_item_index
            visible_item_index += 1

            # Process answer/hint (unchanged)
            item.combined_answer = (
                item.answer.strip()
                if (item.answer and item.answer.strip())
                else "No answer provided"
            )
            item.display_hint = (
                item.hint.strip()
                if (item.hint and item.hint.strip())
                else "No hint available"
            )

            # Add to processed items (passed to template)
            processed_items.append(item)

    # 9. Pass data to template (use processed_items = only visible items)
    context = {
        "activity": activity,
        "items": processed_items,  # Filtered: only continue_revision=True
        "total_items": len(processed_items),
        "course_id": activity.lesson.course.id,
        "activities": activities,
        "previous_activity": previous_activity,
        "next_activity": next_activity,
    }

    # 10. Render template
    return render(request, "course/view_items.html", context)


@require_POST
@login_required
def submit_activity_view(request, activity_id):
    try:
        student_profile = request.user.profile
        responses = json.loads(request.POST.get("responses", "[]"))
        is_completed = request.POST.get("is_completed", "false").lower() == "true"
        revised_count = int(
            request.POST.get("revised_count", 0)
        )  # 接收前端传递的本轮修订数
        activity = get_object_or_404(Activity, pk=activity_id)

        with transaction.atomic():
            if responses:
                for response in responses:
                    item_id = response.get("item_id")
                    successes = response.get("successes", 0)
                    continue_revision = response.get(
                        "continue_revision", True
                    )  # bool from frontend
                    revise_at_str = response.get("revise_at")  # e.g., "2099-12-31"
                    next_1 = response.get("next_1", 1)
                    next_2 = response.get("next_2", 1)

                    try:
                        student_item = StudentItem.objects.get(
                            student=student_profile, item_id=item_id
                        )
                    except StudentItem.DoesNotExist:
                        student_item = None

                    # Default values
                    defaults = {
                        "successes": successes,
                        "is_master": successes >= 3,
                        "updated_at": timezone.now(),
                    }

                    # CASE 1: User clicked "Skip future revision" → trust frontend values completely
                    if not continue_revision:
                        # Convert revise_at string to timezone-aware datetime
                        if revise_at_str:
                            try:
                                revise_at_dt = datetime.fromisoformat(revise_at_str)
                                if revise_at_dt.tzinfo is None:
                                    revise_at_dt = revise_at_dt.replace(
                                        tzinfo=ZoneInfo("UTC")
                                    )
                            except ValueError:
                                revise_at_dt = datetime(
                                    2099, 12, 31, tzinfo=ZoneInfo("UTC")
                                )
                        else:
                            revise_at_dt = datetime(
                                2099, 12, 31, tzinfo=ZoneInfo("UTC")
                            )

                        defaults.update(
                            {
                                "continue_revision": False,
                                "revise_at": revise_at_dt,
                                "next_1": 9999,
                                "next_2": 9999,
                                "is_master": True,  # Skipped items are considered mastered
                            }
                        )

                    # CASE 2: Normal practice → apply spaced repetition logic
                    else:
                        current_next_1 = student_item.next_1 if student_item else 1
                        current_next_2 = student_item.next_2 if student_item else 1
                        current_revise_at = (
                            student_item.revise_at if student_item else None
                        )

                        is_master = successes >= 3

                        if is_master:
                            if current_revise_at and timezone.now() < current_revise_at:
                                # Early review
                                defaults.update(
                                    {
                                        "revise_at": timezone.now()
                                        + timedelta(days=current_next_2),
                                        "next_1": current_next_1,
                                        "next_2": current_next_2,
                                    }
                                )
                            else:
                                # Normal progression
                                defaults.update(
                                    {
                                        "revise_at": timezone.now()
                                        + timedelta(days=current_next_2),
                                        "next_1": current_next_2,
                                        "next_2": current_next_1 + current_next_2,
                                    }
                                )
                        else:
                            # Not mastered yet
                            defaults.update(
                                {
                                    "revise_at": current_revise_at or timezone.now(),
                                    "next_1": current_next_1,
                                    "next_2": current_next_2,
                                }
                            )

                        defaults["continue_revision"] = True

                    # Create or update the StudentItem
                    student_item_obj, created = StudentItem.objects.update_or_create(
                        student=student_profile,
                        item_id=item_id,
                        defaults=defaults,
                    )

                    if created:
                        student_item_obj.start_at = timezone.now()
                        student_item_obj.save()

            # Update activity progress (count mastered + skipped items)
            total_items = Item.objects.filter(activity=activity).count()
            mastered_items = StudentItem.objects.filter(
                student=student_profile,
                item__activity=activity,
                is_master=True,
            ).count()

            progress = (mastered_items / total_items) * 100 if total_items > 0 else 0
            completed_status = is_completed or progress >= 100

            # Update StudentActivity
            student_activity, _ = StudentActivity.objects.update_or_create(
                student=student_profile,
                activity=activity,
                defaults={
                    "progress": progress,
                    "completed": completed_status,
                    "updated_at": timezone.now(),
                },
            )

            # 新增：获取累计修订数（从StudentActivity或自定义存储中获取，这里简化为累加）
            # 若需持久化累计修订数，建议在StudentActivity中添加cumulative_revised_items字段
            cumulative_revised = (
                getattr(student_activity, "cumulative_revised_items", 0) + revised_count
            )
            # 可选：更新StudentActivity的累计修订数字段
            student_activity.cumulative_revised_items = cumulative_revised
            student_activity.save()

        # 新增：判断是否为AJAX请求，返回JSON（前端无刷新）或重定向
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {
                    "status": "success",
                    "stats": {
                        "cumulative_revised_items": cumulative_revised,
                        "mastered_items": mastered_items,
                        "total_items": total_items,
                        "progress": round(progress, 1),
                    },
                }
            )
        else:
            return redirect("course:activity_detail", activity_id=activity_id)

    except Exception as e:
        # 异常处理：AJAX请求返回错误JSON，普通请求重定向
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
        else:
            raise e


@login_required
def enroll_view(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    student_profile = request.user.profile

    # Check if already enrolled (optional - handled by model but good for user feedback)
    if StudentCourse.objects.filter(student=student_profile, course=course).exists():
        messages.warning(request, "You are already enrolled in this course")
        return redirect("course", course_id=course.id)

    # Create enrollment
    try:
        StudentCourse.objects.create(
            student=student_profile,
            course=course,  # Initial progress
        )
        # messages.success(request, "Successfully enrolled in the course!")
        messages.success(request, f"Successfully enrolled in course - {course.title}")
    except IntegrityError:  # In case unique constraint fails
        messages.warning(request, "You are already enrolled in this course")

    return redirect("student_courses")


@require_POST
@login_required
def unsubscribe_course(request, course_id):
    student_profile = request.user.profile
    course = get_object_or_404(Course, id=course_id)
    try:
        # Delete all related items and activities in a single transaction
        with transaction.atomic():
            # Get the student course enrollment
            enrollment = StudentCourse.objects.get(
                student=student_profile, course=course
            )

            # Delete all related student items (through: course → lesson → activity → item)
            StudentItem.objects.filter(
                student=student_profile, item__activity__lesson__course=course
            ).delete()

            # Delete all related student activities (through: course → lesson → activity)
            StudentActivity.objects.filter(
                student=student_profile, activity__lesson__course=course
            ).delete()

            # Finally delete the course enrollment
            enrollment.delete()

        # messages.success(request, f"Successfully unsubscribed from {course.title}")
        messages.success(
            request, f"Successfully unsubscribed from course - {course.title}"
        )

    except StudentCourse.DoesNotExist:
        messages.error(request, "You are not enrolled in this course")
    except Exception as e:
        messages.error(request, f"Error unsubscribing: {str(e)}")

    return redirect(
        "student_courses"
    )  # Redirect to course list or another appropriate page
