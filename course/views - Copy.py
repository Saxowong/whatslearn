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
from django.urls import reverse
from django.utils import timezone
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

import json
from random import sample, shuffle
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

    first_course_activity_subquery = Activity.objects.filter(
        lesson__course=OuterRef("course")
    ).order_by("id").values("id")[:1]

    latest_student_activity_subquery = StudentActivity.objects.filter(
        student=user,
        activity__lesson__course=OuterRef("course")
    ).order_by("-updated_at").values("activity_id")[:1]

    first_student_activity_subquery = StudentActivity.objects.filter(
        student=user,
        activity__lesson__course=OuterRef("course")
    ).order_by("updated_at").values("activity_id")[:1]

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
                output_field=IntegerField()
            ),
            first_activity_id=Coalesce(
                Subquery(first_student_activity_subquery, output_field=IntegerField()),
                Subquery(first_course_activity_subquery, output_field=IntegerField()),
                output_field=IntegerField()
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
    unenrolled_courses = Course.objects.exclude(
        id__in=StudentCourse.objects.filter(student=user).values("course_id")
    ).filter(
        is_published=True
    ).order_by(
        "-created_at"
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
            "item__question",
            "item__answer",
            "item__image",
            "item__audio",
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
            .exclude(
                id__in=[item["id"] for item in items]
            )  # Exclude already selected items
            .select_related("item__activity")
            .values(
                "id",
                "item__id",
                "item__question",
                "item__answer",
                "item__image",
                "item__audio",
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

    # Get all possible answers for generating alternatives
    all_answers = (
        Item.objects.filter(activity__lesson__course=course)
        .exclude(answer__isnull=True)
        .values_list("answer", flat=True)
        .distinct()
    )

    course.revision_items = []
    for item in items:
        item_data = {
            "id": item["id"],
            "item_id": item["item__id"],
            "question": item["item__question"],
            "answer": item["item__answer"],
            "successes": item["successes"],
            "is_master": item["is_master"],
            "next_1": item["next_1"],
            "next_2": item["next_2"],
            "revise_at": (item["revise_at"].isoformat() if item["revise_at"] else None),
            "continue_revision": item["continue_revision"],
        }
        # Generate three alternative wrong answers
        wrong_answers = list(set(all_answers) - {item["item__answer"]})
        wrong_answers = (
            wrong_answers[:3]
            if len(wrong_answers) >= 3
            else wrong_answers
            + ["Option " + str(i) for i in range(1, 4 - len(wrong_answers) + 1)]
        )
        item_data["wrong_answers"] = wrong_answers

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
                            total_items=Count("items"),
                            mastered_items=Coalesce(
                                Subquery(
                                    StudentItem.objects.filter(
                                        student=student_profile,
                                        item__activity=OuterRef("pk"),
                                        successes__gte=3,
                                    )
                                    .values("item__activity")
                                    .annotate(count=Count("pk"))
                                    .values("count")[:1],
                                    output_field=IntegerField(),
                                ),
                                0,
                            ),
                            student_progress=Coalesce(
                                ExpressionWrapper(
                                    (F("mastered_items") / F("total_items")) * 100,
                                    output_field=FloatField(),
                                ),
                                0.0,
                                output_field=FloatField(),
                            ),
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
            revision_items_count=Subquery(
                StudentItem.objects.filter(
                    student=student_profile,
                    item__activity__lesson__course=OuterRef("pk"),
                    revise_at__lte=timezone.now(),
                )
                .values("student")
                .annotate(count=Count("id"))
                .values("count")[:1],
                output_field=IntegerField()
            ),
            activities_completed=Subquery(
                StudentActivity.objects.filter(
                    student=student_profile,
                    activity__lesson__course=OuterRef("pk"),
                    completed=True
                )
                .values("student")
                .annotate(count=Count("id"))
                .values("count")[:1],
                output_field=IntegerField()
            ),
            exercise_items_mastered=Subquery(
                StudentItem.objects.filter(
                    student=student_profile,
                    item__activity__lesson__course=OuterRef("pk"),
                    successes__gte=3,
                )
                .values("student")
                .annotate(count=Count("id"))
                .values("count")[:1],
                output_field=IntegerField()
            ),
        ),
        id=course_id,
    )
    # Assign continuous numbering to activities across lessons
    activity_counter = 1
    for lesson in course.lessons.all():
        for activity in lesson.activities.all():
            activity.global_index = activity_counter
            activity_counter += 1
    # Update StudentCourse's updated_at
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
        },
    )

@login_required
def activity_view(request, activity_id):
    # Get the activity and verify course enrollment
    activity = get_object_or_404(
        Activity.objects.select_related("lesson__course"), pk=activity_id
    )
    lesson = activity.lesson
    course = lesson.course
    # Verify enrollment
    if not StudentCourse.objects.filter(
        student=request.user.profile, course=course
    ).exists():
        raise PermissionDenied("You are not enrolled in this course")
    # Get ALL activities in the course in lesson-order + activity-order
    all_activities = (
        Activity.objects
        .filter(lesson__course=course)
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
            )
        )
        .order_by("lesson__order", "order")
    )
    # Assign global index across entire course
    counter = 1
    for a in all_activities:
        a.global_index = counter
        counter += 1
    # Find previous and next activities
    previous_activity = None
    next_activity = None
    all_activities_list = list(all_activities)
    for i, a in enumerate(all_activities_list):
        if a.id == activity.id:
            if i > 0:  # If not the first activity
                previous_activity = all_activities_list[i - 1]
            if i < len(all_activities_list) - 1:  # If not the last activity
                next_activity = all_activities_list[i + 1]
            break
    # Filter the RHS list to only current lesson’s activities, but keep global_index
    lesson_activities = [a for a in all_activities if a.lesson_id == lesson.id]
    # Get or create StudentActivity record for this activity
    student_activity, created = StudentActivity.objects.get_or_create(
        student=request.user.profile,
        activity=activity,
        defaults={"progress": 0.0, "completed": False},
    )
    mastered_items_count = 0
    if activity.activity_type == "exercise":
        total_items = activity.items.count()
        mastered_items_count = StudentItem.objects.filter(
            student=request.user.profile, item__activity=activity, is_master=True
        ).count()
        progress = (
            (mastered_items_count / total_items) * 100 if total_items > 0 else 0.0
        )
        student_activity.progress = progress
        student_activity.completed = progress >= 100
        student_activity.save()
    # Always update last accessed time
    student_activity.updated_at = timezone.now()
    student_activity.save(update_fields=["updated_at"])
    context = {
        "activity": activity,
        "student_activity": student_activity,
        "is_enrolled": True,
        "course_id": course.id,
        "mastered_items_count": (
            mastered_items_count if activity.activity_type == "exercise" else 0
        ),
        "progress_percentage": student_activity.progress,
        "activities": lesson_activities,  # RHS lesson activities with global_index
        "previous_activity": previous_activity,  # Added for Previous button
        "next_activity": next_activity,  # Added for Next button
    }
    if activity.activity_type == "exercise":
        items = list(activity.items.all())
        student_items = {
            si.item_id: si
            for si in StudentItem.objects.filter(
                student=request.user.profile, item__in=items
            )
        }
        for item in items:
            student_item = student_items.get(item.id)
            item.successes = student_item.successes if student_item else 0
            item.is_master = student_item.is_master if student_item else False
            item.revise_at = student_item.revise_at if student_item else None
            item.updated_at = student_item.updated_at if student_item else None
            item.next_1 = student_item.next_1 if student_item else 1
            item.next_2 = student_item.next_2 if student_item else 1
            wrong_answers = [
                i.answer for i in items if i.id != item.id and i.answer != item.answer
            ]
            if len(wrong_answers) < 3:
                wrong_answers.extend(
                    ["Alternative option 1", "Alternative option 2"][: 3 - len(wrong_answers)]
                )
            selected_wrong = sample(wrong_answers, 3)
            options = [item.answer] + selected_wrong
            shuffle(options)
            item.options = options
        context["items"] = items
        template_name = "course/exercise_activity.html"
    elif activity.activity_type == "video":
        template_name = "course/video_activity.html"
    else:
        template_name = "course/html_activity.html"
    return render(request, template_name, context)



@require_POST
@login_required
def submit_activity_view(request, activity_id):
    if request.method == "POST":
        student_profile = request.user.profile
        responses = json.loads(request.POST.get("responses", "[]"))
        is_completed = request.POST.get("is_completed", "false").lower() == "true"
        activity = get_object_or_404(Activity, pk=activity_id)

        with transaction.atomic():
            if responses:
                for response in responses:
                    # Get existing StudentItem
                    try:
                        student_item = StudentItem.objects.get(
                            student=student_profile, item_id=response["item_id"]
                        )
                        current_next_1 = student_item.next_1
                        current_next_2 = student_item.next_2
                        current_revise_at = student_item.revise_at
                    except StudentItem.DoesNotExist:
                        current_next_1 = 1
                        current_next_2 = 1
                        current_revise_at = None

                    # Determine if item is mastered
                    is_master = response["successes"] >= 3

                    # Initialize defaults
                    defaults = {
                        "successes": response["successes"],
                        "is_master": is_master,
                        "updated_at": timezone.now(),
                    }
                    # Update revision fields only for mastered items
                    if is_master:
                        if current_revise_at and timezone.now() < current_revise_at:
                            # Review not due: extend revise_at, keep next_1 and next_2 unchanged
                            defaults.update(
                                {
                                    "revise_at": timezone.now()
                                    + timedelta(days=current_next_2),
                                    "next_1": current_next_1,
                                    "next_2": current_next_2,
                                }
                            )
                        else:
                            # Review due/overdue or no revise_at: full update
                            defaults.update(
                                {
                                    "revise_at": timezone.now()
                                    + timedelta(days=current_next_2),
                                    "next_1": current_next_2,
                                    "next_2": current_next_1 + current_next_2,
                                }
                            )
                    else:
                        # Non-mastered: retain existing or default values
                        defaults.update(
                            {
                                "revise_at": current_revise_at or timezone.now(),
                                "next_1": current_next_1,
                                "next_2": current_next_2,
                            }
                        )

                    # Update or create StudentItem
                    student_item, created = StudentItem.objects.update_or_create(
                        student=student_profile,
                        item_id=response["item_id"],
                        defaults=defaults,
                    )

                    # Set start_at for new items
                    if created:
                        student_item.start_at = timezone.now()
                        student_item.save()

                # Update activity progress
                total_items = Item.objects.filter(activity=activity).count()
                mastered_items = StudentItem.objects.filter(
                    student=student_profile, item__activity=activity, successes__gte=3
                ).count()

                progress = (
                    (mastered_items / total_items) * 100 if total_items > 0 else 0
                )
                completed_status = is_completed or progress >= 100
            else:
                # Non-exercise activities
                progress = 0
                completed_status = is_completed

            # Update StudentActivity
            StudentActivity.objects.update_or_create(
                student=student_profile,
                activity=activity,
                defaults={
                    "progress": progress,
                    "completed": completed_status,
                    "updated_at": timezone.now(),
                },
            )

        return redirect("course:activity_detail", activity_id=activity_id)


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

    return redirect("available_courses")


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
