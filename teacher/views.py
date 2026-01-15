from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max, Q
from django.db import transaction
from course.models import Course, Category, Lesson, Activity, Item, StudentCourse
from dictionary.models import DictionaryItem
from django.contrib import messages
from user.models import Profile
from django.urls import reverse
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.conf import settings
from .forms import CourseForm, LessonForm, ActivityForm, ItemForm
import os, zipfile
from django.core.files import File  # <-- ADD THIS IMPORT
import tempfile
from io import BytesIO
import pandas as pd
import uuid, re
import logging

logger = logging.getLogger(__name__)


@login_required
def manage_courses(request):
    courses = (
        Course.objects.filter(teacher__user=request.user)
        .select_related("teacher__user", "category")  # Only for fields used in template
        .annotate(
            lesson_count=Count(
                "lessons", distinct=True
            ),  # Use distinct to avoid join inflation
            enrollment_count=Count("student_courses", distinct=True),
        )
    )
    # Debug: Log counts for verification
    for course in courses:
        print(
            f"Course: {course.title}, Lessons: {course.lesson_count}, Raw Lessons: {course.lessons.count()}, "
            f"Enrollments: {course.enrollment_count}, Raw Enrollments: {course.student_courses.count()}"
        )
    context = {
        "courses": courses,
        "categories": Category.objects.all(),
    }
    return render(request, "teacher/manage_courses.html", context)


@login_required
def manage_learners(request, course_id):
    # Fetch the course, ensuring it belongs to the teacher
    course = get_object_or_404(
        Course.objects.select_related("teacher", "category"),
        id=course_id,
        teacher__user=request.user,
    )
    # Fetch enrolled students with annotations for course count and activities completed
    students = (
        StudentCourse.objects.filter(course=course)
        .select_related("student__user")
        .annotate(
            course_count=Count("student__student_courses__course", distinct=True),
            activities_completed=Count(
                "student__student_activities",
                filter=Q(
                    student__student_activities__completed=True,
                    student__student_activities__activity__lesson__course__id=course.id,
                ),
            ),
        )
    )
    context = {
        "course": course,
        "students": students,
    }
    return render(request, "teacher/manage_learners.html", context)


@login_required
def edit_course(request, course_id=0):
    categories = Category.objects.all()

    if course_id:
        course = get_object_or_404(Course, id=course_id, teacher__user=request.user)
    else:
        course = None

    if request.method == "POST":
        form = CourseForm(request.POST, request.FILES, instance=course)
        if form.is_valid():
            course = form.save(commit=False)
            if not course_id:
                try:
                    course.teacher = request.user.profile
                except Profile.DoesNotExist:
                    error = "User profile not found. Please create a profile before creating a course."
                    return render(
                        request,
                        "teacher/edit_course.html",
                        {
                            "course": course or {},
                            "categories": categories,
                            "error": error,
                            "form": form,
                        },
                    )
            # Save the course to generate an ID (for new courses)
            course.save()
            # Update file fields only if new files are uploaded
            files_updated = False
            if "image" in request.FILES:
                course.image = request.FILES["image"]
                files_updated = True
            if "video" in request.FILES:
                course.video = request.FILES["video"]
                files_updated = True
            # Save again only if files were updated
            if files_updated:
                course.save()
            return redirect("teacher:manage_courses")
        else:
            error = "Please correct the errors below"
    else:
        form = CourseForm(instance=course)
        error = None

    return render(
        request,
        "teacher/edit_course.html",
        {
            "course": course or {},
            "categories": categories,
            "error": error,
            "form": form,  # Pass form to template for rendering
        },
    )


@login_required
def delete_course(request, course_id):
    # Fetch the course, ensuring it belongs to the user
    course = get_object_or_404(Course, id=course_id, teacher__user=request.user)
    if request.method == "POST":
        course_title = course.title  # Store title for message
        course.delete()
        messages.success(request, f"'{course_title}' deleted successfully.")
        return HttpResponseRedirect(reverse("teacher:manage_courses"))
    return HttpResponseRedirect(reverse("teacher:manage_courses"))

    # For non-POST requests, return 405 Method Not Allowed
    return HttpResponse(status=405)


@login_required
def manage_lessons(request, course_id):
    course = get_object_or_404(Course, id=course_id, teacher__user=request.user)
    lessons = (
        Lesson.objects.filter(course=course)
        .annotate(activity_count=Count("activities"))
        .order_by("order")
    )

    def resequence_lessons(course):
        """Resequence all lessons for the course to ensure orders are 1 to N."""
        lessons = Lesson.objects.filter(course=course).order_by("order", "created_at")
        for index, lesson in enumerate(lessons, start=1):
            lesson.order = index
            lesson.save()

    if request.method == "POST":
        if "action" in request.POST and request.POST["action"] == "reorder":
            try:
                lesson_orders = []
                for key, value in request.POST.items():
                    if key.startswith("order_"):
                        lesson_id = key.split("_")[1]
                        try:
                            order = int(value)
                            lesson_orders.append((lesson_id, order))
                        except ValueError:
                            messages.error(
                                request,
                                f"Invalid order value for lesson ID {lesson_id}",
                            )
                            return redirect(
                                "teacher:manage_lessons", course_id=course.id
                            )

                lesson_orders.sort(key=lambda x: x[1])
                for index, (lesson_id, _) in enumerate(lesson_orders, start=1):
                    lesson = Lesson.objects.get(id=lesson_id, course=course)
                    lesson.order = index
                    lesson.save()

                messages.success(request, "Lesson order saved successfully.")
                return redirect("teacher:manage_lessons", course_id=course.id)

            except Lesson.DoesNotExist:
                messages.error(request, "One or more lessons not found.")
                return redirect("teacher:manage_lessons", course_id=course.id)

        form = LessonForm(request.POST)
        if form.is_valid():
            if "lesson_id" in request.POST and request.POST.get("action") == "update":
                try:
                    lesson = Lesson.objects.get(
                        id=request.POST["lesson_id"], course=course
                    )
                    lesson.title = form.cleaned_data["title"]
                    lesson.order = form.cleaned_data["order"]
                    lesson.save()
                    resequence_lessons(course)  # Resequence after update
                    messages.success(request, "Lesson updated successfully.")
                    return redirect("teacher:manage_lessons", course_id=course.id)
                except Lesson.DoesNotExist:
                    messages.error(request, "Lesson not found.")
                    return redirect("teacher:manage_lessons", course_id=course.id)
            else:
                lesson = form.save(commit=False)
                lesson.course = course
                lesson.order = form.cleaned_data["order"]
                lesson.save()
                resequence_lessons(course)  # Resequence after create
                messages.success(request, "Lesson added successfully.")
                return redirect("teacher:manage_lessons", course_id=course.id)
        else:
            messages.error(request, "Error processing lesson. Please check the form.")

    else:
        form = LessonForm()

    return render(
        request,
        "teacher/manage_lessons.html",
        {
            "course": course,
            "lessons": lessons,
            "form": form,
        },
    )


@login_required
def edit_lesson(request, lesson_id=0):

    lesson = get_object_or_404(Lesson, id=lesson_id) if lesson_id else None

    if request.method == "POST":
        form = LessonForm(request.POST, request.FILES, instance=lesson)
        if form.is_valid():
            lesson = form.save(commit=False)
            if not lesson_id:
                try:
                    lesson.teacher = request.user.profile
                except Profile.DoesNotExist:
                    error = "User profile not found. Please create a profile before creating a course."
                    return render(
                        request,
                        "teacher/edit_lesson.html",
                        {
                            "lesson": lesson or {},
                            "error": error,
                            "form": form,
                        },
                    )
            # Save the course to generate an ID (for new courses)
            lesson.save()
            # Update file fields only if new files are uploaded

            return redirect("teacher:manage_lessons")
        else:
            error = "Please correct the errors below"
    else:
        form = LessonForm(instance=lesson)
        error = None

    return render(
        request,
        "teacher/edit_lesson.html",
        {
            "lesson": lesson or {},
            "error": error,
            "form": form,  # Pass form to template for rendering
        },
    )


@login_required
def delete_lesson(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id, course__teacher__user=request.user)
    course = lesson.course  # Get the course from the lesson

    if request.method == "POST":
        with transaction.atomic():
            lesson_title = lesson.title
            lesson.delete()
            messages.success(request, f"Lesson '{lesson_title}' deleted successfully.")

            # Resequence the order field for remaining lessons
            remaining_lessons = Lesson.objects.filter(course=course).order_by("order")
            for index, lesson in enumerate(remaining_lessons, start=1):
                lesson.order = index
                lesson.save()

        # Redirect to the manage_lessons view with the course ID
        response = redirect("teacher:manage_lessons", course_id=course.id)
        response["Cache-Control"] = "no-cache, no-store, must_revalidate"
        return response

    # For non-POST requests, return 405 Method Not Allowed
    return HttpResponse(status=405)


@login_required
def manage_activities(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id, course__teacher__user=request.user)
    course = lesson.course
    activities = Activity.objects.filter(lesson=lesson).order_by("order")

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "reorder":
            order_data = []
            for key in request.POST:
                if key.startswith("order_"):
                    activity_id = key.replace("order_", "")
                    try:
                        order = int(request.POST[key])
                        order_data.append({"activity_id": activity_id, "order": order})
                    except ValueError:
                        messages.error(request, "Invalid order value provided.")
                        return redirect(
                            "teacher:manage_activities", lesson_id=lesson.id
                        )
            if not order_data:
                messages.error(request, "No activities to reorder.")
                return redirect("teacher:manage_activities", lesson_id=lesson.id)
            # Validate activity IDs
            activity_ids = [item["activity_id"] for item in order_data]
            valid_activities = Activity.objects.filter(
                id__in=activity_ids, lesson=lesson
            )
            if len(valid_activities) != len(activity_ids):
                messages.error(request, "Invalid activity IDs provided.")
                return redirect("teacher:manage_activities", lesson_id=lesson.id)
            # Sort by order and assign sequential numbers
            sorted_orders = sorted(order_data, key=lambda x: x["order"])
            for index, item in enumerate(sorted_orders, start=1):
                activity = Activity.objects.get(id=item["activity_id"], lesson=lesson)
                activity.order = index
                activity.save()
            messages.success(request, "Activity order saved successfully.")
            return redirect("teacher:manage_activities", lesson_id=lesson.id)
        else:
            activity_id = request.POST.get("activity_id")
            if activity_id:  # Update existing activity
                activity = get_object_or_404(Activity, id=activity_id, lesson=lesson)
                form = ActivityForm(request.POST, instance=activity)
                if form.is_valid():
                    activity = form.save(commit=False)
                    activity.lesson = lesson
                    activity.save()
                    # Reorder activities
                    all_activities = Activity.objects.filter(lesson=lesson).order_by(
                        "order", "id"
                    )
                    for index, activity in enumerate(all_activities, start=1):
                        activity.order = index
                        activity.save()
                    messages.success(
                        request, f"Activity '{activity.title}' updated successfully."
                    )
                    return redirect("teacher:manage_activities", lesson_id=lesson.id)
                else:
                    messages.error(request, "Please correct the errors below.")
            else:  # Create new activity
                form = ActivityForm(request.POST)
                if form.is_valid():
                    activity = form.save(commit=False)
                    activity.lesson = lesson
                    activity.save()
                    # Reorder activities
                    all_activities = Activity.objects.filter(lesson=lesson).order_by(
                        "order", "id"
                    )
                    for index, activity in enumerate(all_activities, start=1):
                        activity.order = index
                        activity.save()
                    messages.success(
                        request, f"Activity '{activity.title}' created successfully."
                    )
                    return redirect("teacher:manage_activities", lesson_id=lesson.id)
                else:
                    messages.error(request, "Please correct the errors below.")
    else:
        form = ActivityForm(initial={"order": activities.count() + 1})

    context = {
        "course": course,
        "lesson": lesson,
        "activities": activities,
        "form": form,
        "activity_types": Activity.ACTIVITY_TYPES,
    }
    return render(request, "teacher/manage_activities.html", context)


@login_required
def edit_activity(request, lesson_id, activity_id=0):
    lesson = get_object_or_404(Lesson, id=lesson_id, course__teacher__user=request.user)
    activity = (
        get_object_or_404(Activity, id=activity_id, lesson=lesson)
        if activity_id
        else None
    )

    raw_srt_content = ""
    if activity and activity.activity_type == "reading" and activity.html_content:
        raw_srt_content = activity.html_content

    if request.method == "POST":
        form = ActivityForm(request.POST, request.FILES, instance=activity)

        if form.is_valid():
            activity = form.save(commit=False)
            activity.lesson = lesson

            # Save RAW SRT to html_content
            if request.POST.get("activity_type") == "reading":
                activity.html_content = request.POST.get("srt_content", "").strip()

                # Save clean audio file (no activity prefix)
                audio_file_url = request.POST.get("audio_file_url")
                if audio_file_url and audio_file_url.startswith(settings.MEDIA_URL):
                    audio_relative_path = audio_file_url.replace(
                        settings.MEDIA_URL, ""
                    ).lstrip("/")
                    audio_file_path = os.path.join(
                        settings.MEDIA_ROOT, audio_relative_path
                    )

                    if os.path.exists(audio_file_path):
                        try:
                            with open(audio_file_path, "rb") as f:
                                django_file = File(f)
                                # Extract JUST the original filename (no path/activity prefix)
                                filename = os.path.basename(audio_file_path)
                                activity.audio_file.save(
                                    filename, django_file, save=False
                                )
                        except Exception as e:
                            logger.error(f"Error saving audio: {str(e)}")

                # Handle YouTube link conversion
                youtube_link = request.POST.get("reading_youtube_link")
                if youtube_link:
                    youtube_pattern = r"(?:youtu\.be\/|youtube\.com\/(?:watch\?v=|embed\/|v\/))([^&\n?]+)"
                    video_id_match = re.search(youtube_pattern, youtube_link)
                    if video_id_match:
                        video_id = video_id_match.group(1)
                        activity.video_embed_code = f'<iframe width="560" height="315" src="https://www.youtube.com/embed/{video_id}" frameborder="0" allowfullscreen></iframe>'

            # Save activity (includes clean audio file reference)
            activity.save()

            # Handle PDF upload (unchanged)
            if (
                form.cleaned_data["activity_type"] == "pdf"
                and "pdf_file" in request.FILES
            ):
                if activity.pdf_file:
                    old_pdf_path = activity.pdf_file.path
                    if os.path.exists(old_pdf_path):
                        try:
                            os.remove(old_pdf_path)
                        except Exception as e:
                            logger.error(f"PDF deletion error: {str(e)}")

                pdf_file = request.FILES["pdf_file"]
                media_path = os.path.join("courses", str(lesson.course.id))
                full_media_path = os.path.join(settings.MEDIA_ROOT, media_path)
                os.makedirs(full_media_path, exist_ok=True)
                filename = os.path.basename(pdf_file.name)
                activity.pdf_file.save(os.path.join(media_path, filename), pdf_file)

            # Resequence activities
            activities = Activity.objects.filter(lesson=lesson).order_by(
                "order", "created_at"
            )
            for index, act in enumerate(activities, start=1):
                act.order = index
                act.save()

            return redirect("teacher:manage_activities", lesson_id=lesson.id)
        else:
            logger.error(f"Form errors: {form.errors.as_json()}")
            error = "Please correct the errors below"
    else:
        form = ActivityForm(instance=activity)
        error = None

    return render(
        request,
        "teacher/edit_activity.html",
        {
            "activity": activity,
            "lesson": lesson,
            "error": error,
            "form": form,
            "activity_types": Activity.ACTIVITY_TYPES,
            "raw_srt_content": raw_srt_content,
        },
    )


# Keep your existing upload_audio view (ensure it's also properly imported)
@csrf_exempt
def upload_audio(request):
    if request.method == "POST" and request.FILES.get("audio_file"):
        try:
            # Get file and metadata
            audio_file = request.FILES["audio_file"]
            lesson_id = request.POST.get("lesson_id")

            # Validate file type
            if (
                not audio_file.name.lower().endswith(".mp3")
                and audio_file.content_type != "audio/mpeg"
            ):
                return JsonResponse(
                    {"success": False, "error": "Only MP3 files are allowed!"}
                )

            # Get course ID from lesson (direct course-level organization)
            lesson = get_object_or_404(Lesson, id=lesson_id)
            course_id = lesson.course.id

            # Create upload path (DIRECTLY under course folder: courses/7/)
            upload_dir = os.path.join("courses", str(course_id))  # No audio subfolder
            full_upload_dir = os.path.join(settings.MEDIA_ROOT, upload_dir)
            os.makedirs(full_upload_dir, exist_ok=True)

            # Use ORIGINAL filename (no activity ID prefix)
            filename = audio_file.name
            # Add unique suffix only if file exists (prevent overwrites)
            file_path = os.path.join(upload_dir, filename)
            counter = 1
            while default_storage.exists(file_path):
                base, ext = os.path.splitext(filename)
                filename = f"{base}_{counter}{ext}"
                file_path = os.path.join(upload_dir, filename)
                counter += 1

            # Save file with clean filename (no activity_70_ prefix)
            file_path = default_storage.save(file_path, audio_file)

            # Return clean URL (e.g., /media/courses/7/37_-_audio_mDZJnds.mp3)
            audio_url = os.path.join(settings.MEDIA_URL, file_path).replace("\\", "/")
            return JsonResponse(
                {"success": True, "audio_url": audio_url, "file_name": filename}
            )

        except Exception as e:
            logger.error(f"Audio upload error: {str(e)}")
            return JsonResponse({"success": False, "error": f"Upload failed: {str(e)}"})

    return JsonResponse(
        {"success": False, "error": "No file uploaded or invalid request!"}
    )


@login_required
def delete_activity(request, activity_id):
    activity = get_object_or_404(
        Activity, id=activity_id, lesson__course__teacher__user=request.user
    )
    lesson_id = activity.lesson.id

    if request.method == "POST":
        try:
            with transaction.atomic():
                activity_title = activity.title or "Untitled"
                activity.delete()
                logger.debug(f"Activity '{activity_title}' deleted successfully")

                # Resequence orders for remaining activities
                remaining_activities = Activity.objects.filter(
                    lesson_id=lesson_id
                ).order_by("order")
                for index, activity in enumerate(remaining_activities, start=1):
                    activity.order = index
                    activity.save()

            messages.success(
                request, f"Activity '{activity_title}' deleted successfully."
            )
            return HttpResponseRedirect(
                reverse("teacher:manage_activities", args=[lesson_id])
            )
        except Exception as e:
            logger.error(f"Error deleting activity '{activity_title}': {str(e)}")
            messages.error(request, f"Error deleting activity: {str(e)}")
            return HttpResponseRedirect(
                reverse("teacher:manage_activities", args=[lesson_id])
            )

    messages.error(request, "Invalid request method.")
    return HttpResponseRedirect(reverse("teacher:manage_activities", args=[lesson_id]))


@login_required
def manage_items(request, activity_id):
    activity = get_object_or_404(
        Activity, id=activity_id, lesson__course__teacher__user=request.user
    )
    items = Item.objects.filter(activity=activity).order_by("order")

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "reorder":
            order_data = []
            for key in request.POST:
                if key.startswith("order_"):
                    item_id = key.replace("order_", "")
                    try:
                        order = int(request.POST[key])
                        order_data.append({"item_id": item_id, "order": order})
                    except ValueError:
                        messages.error(request, "Invalid order value provided.")
                        return redirect("teacher:manage_items", activity_id=activity.id)

            if not order_data:
                messages.error(request, "No items to reorder.")
                return redirect("teacher:manage_items", activity_id=activity.id)

            # Validate item IDs
            item_ids = [item["item_id"] for item in order_data]
            valid_items = Item.objects.filter(id__in=item_ids, activity=activity)
            if len(valid_items) != len(item_ids):
                messages.error(request, "Invalid item IDs provided.")
                return redirect("teacher:manage_items", activity_id=activity.id)

            # Sort by order and assign sequential numbers
            sorted_orders = sorted(order_data, key=lambda x: x["order"])
            for index, item in enumerate(sorted_orders, start=1):
                item_obj = Item.objects.get(id=item["item_id"], activity=activity)
                item_obj.order = index
                item_obj.save()

            messages.success(request, "Item order saved successfully.")
            return redirect("teacher:manage_items", activity_id=activity.id)

    context = {
        "activity": activity,
        "items": items,
    }
    return render(request, "teacher/manage_items.html", context)


@login_required
def edit_item(request, activity_id, item_id):
    activity = get_object_or_404(Activity, id=activity_id)
    course = activity.lesson.course
    lesson = activity.lesson

    # 1. Fetch the existing item (if editing) - keep this as a separate variable (no shadowing later)
    existing_item = (
        get_object_or_404(Item, id=item_id, activity=activity) if item_id else None
    )

    if request.method == "POST":
        # 2. Bind form to existing item (if editing) and POST data/FILES
        form = ItemForm(request.POST, request.FILES, instance=existing_item)

        if form.is_valid():
            # 3. Get stale old file paths FROM THE EXISTING ITEM (not the form's new item)
            old_image_path = None
            old_audio_path = None
            if existing_item:
                old_image_path = (
                    existing_item.image.path if existing_item.image else None
                )
                old_audio_path = (
                    existing_item.audio.path if existing_item.audio else None
                )

            # 4. Create media directory if needed (unchanged)
            media_path = os.path.join("courses", str(course.id), str(activity.id))
            full_media_path = os.path.join(settings.MEDIA_ROOT, media_path)
            os.makedirs(full_media_path, exist_ok=True)

            # 5. Save form to new item instance (NO VARIABLE SHADOWING - use a new variable name)
            # This is the updated item with the form's data (including the new answer value)
            updated_item = form.save(commit=False)

            # 6. Explicitly set activity (preserve existing logic)
            updated_item.activity = activity

            # 7. Set number_answers based on item_type (unchanged, but applied to updated_item)
            if updated_item.item_type in ["mc", "card"]:
                updated_item.number_answers = 1
            # For 'blank' items, number_answers is set by the form (based on blanks)

            # --------------------------
            # CRITICAL: Explicitly log the answer value from the form's updated item
            # Ensures we can confirm the answer is present before file handling/saving
            # --------------------------
            logger.info(
                f"Preparing to save - Item Type: {updated_item.item_type}, "
                f"Updated Answer: '{updated_item.answer}', "
                f"Item ID: {updated_item.id if updated_item.id else 'New Item'}"
            )

            # 8. Handle file uploads (use old paths from existing_item, new data from updated_item)
            if "image" in request.FILES:
                image_file = request.FILES["image"]
                # Delete old image if exists (from existing_item)
                if old_image_path and os.path.exists(old_image_path):
                    try:
                        os.remove(old_image_path)
                        logger.info(f"Deleted old image: {old_image_path}")
                    except Exception as e:
                        logger.error(f"Error deleting old image file: {str(e)}")
                # Save new image with original filename (to updated_item)
                filename = os.path.basename(image_file.name)
                updated_item.image.save(os.path.join(media_path, filename), image_file)

            if "audio" in request.FILES:
                audio_file = request.FILES["audio"]
                # Delete old audio if exists (from existing_item)
                if old_audio_path and os.path.exists(old_audio_path):
                    try:
                        os.remove(old_audio_path)
                        logger.info(f"Deleted old audio: {old_audio_path}")
                    except Exception as e:
                        logger.error(f"Error deleting old audio file: {str(e)}")
                # Save new audio with original filename (to updated_item)
                filename = os.path.basename(audio_file.name)
                updated_item.audio.save(os.path.join(media_path, filename), audio_file)

            # 9. CRITICAL: Save the updated item (persists the form's answer value to the database)
            # This is the key step that was at risk of failure due to variable shadowing
            updated_item.save()

            # 10. Reorder items (unchanged, but use updated_item's activity)
            all_items = Item.objects.filter(activity=activity).order_by("order", "id")
            for index, itm in enumerate(all_items, start=1):
                itm.order = index
                itm.save()

            # 11. Success message (use updated_item's title)
            messages.success(
                request,
                f"Item '{updated_item.title}' {'updated' if existing_item else 'created'} successfully.",
            )

            # 12. Redirect (unchanged)
            return redirect(
                "teacher:manage_items",
                activity_id=activity.id,
            )
        else:
            # 13. Log form errors for debugging (critical for tracking answer field issues)
            logger.error(f"Form is invalid - Errors: {form.errors}")
            error = "Please correct the errors below"
    else:
        # 14. Initialize form for GET request (unchanged, but use existing_item)
        initial = (
            {
                "order": Item.objects.filter(activity=activity).count() + 1,
                "number_answers": 1,
            }
            if not existing_item
            else {
                "number_answers": (
                    1
                    if existing_item.item_type in ["mc", "card"]
                    else existing_item.number_answers
                )
            }
        )
        form = ItemForm(instance=existing_item, initial=initial)
        error = None

    # 15. Render template (pass existing_item as 'item' for template use)
    return render(
        request,
        "teacher/edit_item.html",
        {
            "item": existing_item or {},
            "lesson": lesson,
            "activity": activity,
            "error": error,
            "form": form,
        },
    )


@login_required
def delete_item(request, item_id):
    item = get_object_or_404(
        Item, id=item_id, activity__lesson__course__teacher__user=request.user
    )
    activity_id = item.activity.id
    lesson_id = item.activity.lesson.id

    if request.method == "POST":
        try:
            with transaction.atomic():
                item_title = item.title or "Untitled"

                # Store file paths before deletion
                media_files = []
                if item.image:
                    media_files.append(item.image.path)
                if item.audio:
                    media_files.append(item.audio.path)

                # Delete the item
                item.delete()
                logger.debug(f"Item '{item_title}' deleted successfully")

                # Delete associated media files
                for file_path in media_files:
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            logger.debug(f"Deleted media file: {file_path}")
                    except Exception as e:
                        logger.error(f"Error deleting media file {file_path}: {str(e)}")
                        # Continue even if file deletion fails

                # Resequence orders for remaining items
                remaining_items = Item.objects.filter(activity_id=activity_id).order_by(
                    "order"
                )
                for index, item in enumerate(remaining_items, start=1):
                    item.order = index
                    item.save()

            messages.success(request, f"Item '{item_title}' deleted successfully.")
            return HttpResponseRedirect(
                reverse("teacher:manage_items", args=[activity_id])
            )
        except Exception as e:
            logger.error(f"Error deleting item '{item_title}': {str(e)}")
            messages.error(request, f"Error deleting item: {str(e)}")
            return HttpResponseRedirect(
                reverse("teacher:manage_items", args=[activity_id])
            )

    messages.error(request, "Invalid request method.")
    return HttpResponseRedirect(reverse("teacher:manage_items", args=[activity_id]))


def find_file_in_directory(directory, filename):
    for root, _, files in os.walk(directory):
        if filename in files:
            return os.path.join(root, filename)
    return None


def save_media_file(src_path, dest_dir, media_path, filename):
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, filename)
    with open(src_path, "rb") as src, open(dest_path, "wb") as dest:
        dest.write(src.read())
    return os.path.join(media_path, filename)


def import_items(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)
    course = activity.lesson.course

    if request.method == "POST":
        zip_file = request.FILES.get("zip_file")
        if not zip_file:
            messages.error(request, "No ZIP file provided")
            return redirect("teacher:manage_items", activity_id=activity.id)

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                zip_path = os.path.join(temp_dir, "upload.zip")
                with open(zip_path, "wb+") as destination:
                    for chunk in zip_file.chunks():
                        destination.write(chunk)

                with zipfile.ZipFile(zip_path, "r") as z:
                    z.extractall(temp_dir)

                excel_files = [
                    f
                    for f in os.listdir(temp_dir)
                    if f.lower().startswith("items.")
                    and f.lower().endswith((".xls", ".xlsx"))
                ]
                if not excel_files:
                    messages.error(
                        request, "No items.xls or items.xlsx found in ZIP file"
                    )
                    return redirect("teacher:manage_items", activity_id=activity.id)

                excel_path = os.path.join(temp_dir, excel_files[0])
                df = pd.read_excel(excel_path)

                required_columns = [
                    "title",
                    "item_type",
                    "item_category",
                    "question",
                    "answer",
                ]
                for col in required_columns:
                    if col not in df.columns:
                        messages.error(request, f"Missing required column: {col}")
                        return redirect("teacher:manage_items", activity_id=activity.id)

                media_path = os.path.join("courses", str(course.id), str(activity.id))
                full_media_path = os.path.join(settings.MEDIA_ROOT, media_path)
                os.makedirs(full_media_path, exist_ok=True)

                current_max_order = (
                    Item.objects.filter(activity=activity).aggregate(Max("order"))[
                        "order__max"
                    ]
                    or 0
                )
                next_order = current_max_order + 1
                valid_item_types = [choice[0] for choice in Item.ITEM_TYPES]

                success_count = 0
                for _, row in df.iterrows():
                    try:
                        item_type = str(row["item_type"]).strip().lower()
                        if item_type not in valid_item_types:
                            messages.error(
                                request,
                                f"Invalid item_type '{item_type}' for item '{row['title']}'",
                            )
                            continue

                        audio_play = str(row["audio_play"]).strip()
                        title = str(row["title"]).strip()
                        question = (
                            str(row["question"]).strip()
                            if pd.notna(row["question"])
                            else ""
                        )
                        answer = (
                            str(row["answer"]).strip()
                            if pd.notna(row["answer"])
                            else ""
                        )
                        hint = str(row["hint"]).strip() if pd.notna(row["hint"]) else ""
                        # --- Special Handling for Flashcards (card type) ---
                        # --- Special Handling for Flashcards (card type) ---
                        if item_type == "card":
                            if not answer and question:
                                try:
                                    dictionary_entry = DictionaryItem.objects.filter(
                                        word__iexact=question.strip()
                                    ).first()

                                    if dictionary_entry:
                                        raw_meaning = dictionary_entry.meaning.strip()

                                        # Split by comma (,) or semicolon (;)
                                        parts = [
                                            p.strip()
                                            for p in re.split(r"[;,]", raw_meaning)
                                        ]
                                        # Remove any empty parts and take only first 3
                                        clean_parts = [p for p in parts if p][:3]

                                        # Rejoin with comma and space
                                        answer = ", ".join(clean_parts)

                                        # Optional: Clean up common prefixes like "C", "U" if you want
                                        # For now, keeping them as they are part of the meaning
                                        # Example: "C兔" → remains "C兔" (or you can strip below)

                                    else:
                                        messages.warning(
                                            request,
                                            f"No dictionary meaning found for word: '{question}' in '{title}'",
                                        )
                                except Exception as e:
                                    messages.warning(
                                        request,
                                        f"Error retrieving dictionary meaning for '{question}': {str(e)}",
                                    )
                            # If answer was provided in Excel, use that instead
                            # (no change needed — already handled above)

                        item_data = {
                            "activity": activity,
                            "title": title,
                            "item_type": item_type,
                            "audio_play": audio_play,
                            "hint": hint,
                            "item_category": (
                                str(row["item_category"])
                                if pd.notna(row["item_category"])
                                else ""
                            ),
                            "order": next_order,
                            "question": question,
                            "answer": answer,  # May now be auto-filled
                            "number_answers": 1,
                        }

                        # Handle answer1–answer4 for MC or blank
                        answer_columns = ["answer1", "answer2", "answer3", "answer4"]
                        if all(col in df.columns for col in answer_columns):
                            for i, col in enumerate(answer_columns, 1):
                                if pd.notna(row.get(col)):
                                    item_data[f"answer{i}"] = str(row[col]).strip()

                        # Handle fill-in-the-blank
                        if item_type == "blank":
                            question_text = item_data["question"]
                            question_text = re.sub(r"_{3,}", "____", question_text)
                            item_data["question"] = question_text
                            blanks = len(re.findall(r"____", question_text))
                            item_data["number_answers"] = blanks if blanks > 0 else 1

                        # Handle multiple choice
                        elif item_type == "mc":
                            if not all(col in df.columns for col in answer_columns):
                                messages.error(
                                    request,
                                    f"Missing answer columns for MC item '{title}'",
                                )
                                continue
                            if not all(pd.notna(row[col]) for col in answer_columns):
                                messages.error(
                                    request,
                                    f"MC item '{title}' must have all four answers",
                                )
                                continue
                            item_data["number_answers"] = 1
                            if pd.notna(row["answer"]):
                                correct = str(row["answer"]).strip()
                                if correct not in [
                                    item_data.get(f"answer{i+1}", "") for i in range(4)
                                ]:
                                    messages.error(
                                        request,
                                        f"Correct answer not in options for MC item '{title}'",
                                    )
                                    continue

                        # Create item
                        item = Item(**item_data)

                        # Handle image
                        if "image_filename" in df.columns and pd.notna(
                            row.get("image_filename")
                        ):
                            img_filename = str(row["image_filename"]).strip()
                            img_path = find_file_in_directory(temp_dir, img_filename)
                            if img_path:
                                item.image = save_media_file(
                                    img_path, full_media_path, media_path, img_filename
                                )

                        # Handle audio
                        if "audio_filename" in df.columns and pd.notna(
                            row.get("audio_filename")
                        ):
                            audio_filename = str(row["audio_filename"]).strip()
                            audio_path = find_file_in_directory(
                                temp_dir, audio_filename
                            )
                            if audio_path:
                                item.audio = save_media_file(
                                    audio_path,
                                    full_media_path,
                                    media_path,
                                    audio_filename,
                                )
                        item.save()
                        success_count += 1
                        next_order += 1

                    except Exception as e:
                        messages.error(
                            request,
                            f"Error processing item '{row.get('title', 'Unknown')}': {str(e)}",
                        )

                messages.success(
                    request,
                    f"Successfully imported {success_count} out of {len(df)} items",
                )
                return redirect("teacher:manage_items", activity_id=activity.id)

        except Exception as e:
            messages.error(request, f"Error processing ZIP file: {str(e)}")
            return redirect("teacher:manage_items", activity_id=activity.id)

    return redirect("teacher:manage_items", activity_id=activity.id)


def export_items(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)

    # Query all items for this activity, ordered
    items = Item.objects.filter(activity=activity).order_by("order")

    # Prepare data for Excel
    data = []
    for item in items:
        data.append(
            {
                "title": item.title or "",
                "item_type": item.item_type or "",
                "item_category": item.item_category or "",
                "question": item.question or "",
                "answer": item.answer or "",
                "hint": item.hint or "",
                "answer1": item.answer1 or "",
                "answer2": item.answer2 or "",
                "answer3": item.answer3 or "",
                "answer4": item.answer4 or "",
                "audio_filename": item.audio.name.split("/")[-1] if item.audio else "",
                "audio_play": item.audio_play or "",
            }
        )

    # Create DataFrame
    df = pd.DataFrame(data)

    # Create in-memory ZIP file
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # Write Excel file
        excel_buffer = BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Items", index=False)
        excel_buffer.seek(0)
        zip_file.writestr("items.xlsx", excel_buffer.getvalue())

        # Add actual audio files if they exist
        for item in items:
            if item.audio and item.audio.name:
                audio_path = item.audio.path
                if os.path.exists(audio_path):
                    zip_file.write(audio_path, os.path.basename(audio_path))

    buffer.seek(0)
    response = HttpResponse(buffer, content_type="application/zip")
    response["Content-Disposition"] = (
        f'attachment; filename="{activity.title}_items_export.zip"'
    )

    return response


def find_file_in_directory(directory, filename):
    """Recursively search for a file in a directory, case-insensitive"""
    for root, _, files in os.walk(directory):
        for f in files:
            if f.lower() == filename.lower():
                return os.path.join(root, f)
    return None


def save_media_file(source_path, dest_dir, media_path, filename):
    """Save media file with unique filename and return its relative path"""
    # Clean filename - remove special characters and spaces
    clean_name = "".join(
        c if c.isalnum() or c in (".", "-", "_") else "_" for c in filename
    )
    clean_name = clean_name.replace(" ", "_")

    # Split filename and extension
    name, ext = os.path.splitext(clean_name)

    # Check if file exists and generate unique name if needed
    counter = 1
    unique_name = clean_name
    while os.path.exists(os.path.join(dest_dir, unique_name)):
        unique_name = f"{name}_{uuid.uuid4().hex[:8]}{ext}"

    dest_path = os.path.join(dest_dir, unique_name)

    # Copy file to media directory
    if os.path.exists(source_path):
        with open(source_path, "rb") as src, open(dest_path, "wb") as dest:
            dest.write(src.read())

    # Return relative path for database
    return os.path.join(media_path, unique_name)
