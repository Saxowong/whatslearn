from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max
from django.db import transaction, models
from course.models import Course, Category, Lesson, Activity, Item
from django.contrib import messages
from user.models import Profile
from django.urls import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.conf import settings
from .forms import CourseForm, LessonForm, ActivityForm, ItemForm, ItemImportForm
import os, zipfile
import tempfile
from io import TextIOWrapper
import pandas as pd
import uuid

import logging

logger = logging.getLogger(__name__)


@login_required
def manage_courses(request):
    # Fetch courses with related teacher, category, and lessons, annotated with lesson count
    courses = (
        Course.objects.filter(teacher__user=request.user)
        .select_related("teacher", "category")
        .prefetch_related("lessons")
        .annotate(lesson_count=Count("lessons"))
    )
    # Debug: Print course data to verify lesson count
    # for course in courses:
    #     # Additional debug: List lesson titles for this course
    #     lesson_titles = [lesson.title for lesson in course.lessons.all()]
    #     print(f"Lessons for Course {course.id}: {lesson_titles}")
    context = {
        "courses": courses,
        "categories": Category.objects.all(),  # For drawer form
    }
    return render(request, "teacher/manage_courses.html", context)


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
    if activity_id:
        activity = get_object_or_404(Activity, id=activity_id, lesson=lesson)
    else:
        activity = None
    if request.method == "POST":
        form = ActivityForm(request.POST, request.FILES, instance=activity)
        if form.is_valid():
            activity = form.save(commit=False)
            if not activity_id:
                activity.lesson = lesson
                activity.save()  # Save to generate activity.id for pdf_media_path
            # Handle PDF file upload
            if "pdf_file" in request.FILES:
                old_pdf_path = activity.pdf_file.path if activity and activity.pdf_file else None
                if old_pdf_path and os.path.exists(old_pdf_path):
                    try:
                        os.remove(old_pdf_path)
                        logger.info(f"Deleted old PDF: {old_pdf_path}")
                    except Exception as e:
                        logger.error(f"Error deleting old PDF: {str(e)}")
                pdf_file = request.FILES["pdf_file"]
                media_path = os.path.join("courses", str(lesson.course.id))
                full_media_path = os.path.join(settings.MEDIA_ROOT, media_path)
                os.makedirs(full_media_path, exist_ok=True)
                filename = os.path.basename(pdf_file.name)
                activity.pdf_file.save(os.path.join(media_path, filename), pdf_file)
            activity.save()
            # Resequence orders after saving
            activities = Activity.objects.filter(lesson=lesson).order_by(
                "order", "created_at"
            )
            for index, act in enumerate(activities, start=1):
                act.order = index
                act.save()
            return redirect("teacher:manage_activities", lesson_id=lesson.id)
        else:
            error = "Please correct the errors below"
    else:
        form = ActivityForm(instance=activity)
        error = None
    return render(
        request,
        "teacher/edit_activity.html",
        {
            "activity": activity or {},
            "lesson": lesson,
            "error": error,
            "form": form,
            "activity_types": Activity.ACTIVITY_TYPES,
        },
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
    item = get_object_or_404(Item, id=item_id, activity=activity) if item_id else None
    if request.method == "POST":
        form = ItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            # Store old file information before saving
            old_image_path = item.image.path if item and item.image else None
            old_audio_path = item.audio.path if item and item.audio else None
            # Create media directory if needed
            media_path = os.path.join("courses", str(course.id), str(activity.id))
            full_media_path = os.path.join(settings.MEDIA_ROOT, media_path)
            os.makedirs(full_media_path, exist_ok=True)
            item = form.save(commit=False)
            item.activity = activity
            # Handle file uploads
            if "image" in request.FILES:
                image_file = request.FILES["image"]
                # Delete old image if exists
                if old_image_path and os.path.exists(old_image_path):
                    try:
                        os.remove(old_image_path)
                        logger.info(f"Deleted old image: {old_image_path}")
                    except Exception as e:
                        logger.error(f"Error deleting old image file: {str(e)}")
                # Save new image with original filename
                filename = os.path.basename(image_file.name)
                item.image.save(os.path.join(media_path, filename), image_file)
            if "audio" in request.FILES:
                audio_file = request.FILES["audio"]
                # Delete old audio if exists
                if old_audio_path and os.path.exists(old_audio_path):
                    try:
                        os.remove(old_audio_path)
                        logger.info(f"Deleted old audio: {old_audio_path}")
                    except Exception as e:
                        logger.error(f"Error deleting old audio file: {str(e)}")
                # Save new audio with original filename
                filename = os.path.basename(audio_file.name)
                item.audio.save(os.path.join(media_path, filename), audio_file)
            item.save()
            # Reorder items
            all_items = Item.objects.filter(activity=activity).order_by("order", "id")
            for index, itm in enumerate(all_items, start=1):
                itm.order = index
                itm.save()
            messages.success(
                request,
                f"Item '{item.title}' {'updated' if item_id else 'created'} successfully.",
            )
            return redirect(
                "teacher:manage_items",
                activity_id=activity.id,
            )
        else:
            error = "Please correct the errors below"
    else:
        initial = (
            {"order": Item.objects.filter(activity=activity).count() + 1}
            if not item
            else {}
        )
        form = ItemForm(instance=item, initial=initial)
        error = None
    return render(
        request,
        "teacher/edit_item.html",
        {
            "item": item or {},
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


def import_items(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)
    course = activity.lesson.course

    if request.method == "POST":
        zip_file = request.FILES.get("zip_file")
        if not zip_file:
            messages.error(request, "No ZIP file provided")
            return redirect(
                "teacher:manage_items",
                lesson_id=activity.lesson.id,
                activity_id=activity.id,
            )

        try:
            # Create temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                # Save uploaded zip to temp location
                zip_path = os.path.join(temp_dir, "upload.zip")
                with open(zip_path, "wb+") as destination:
                    for chunk in zip_file.chunks():
                        destination.write(chunk)

                # Extract ZIP contents
                with zipfile.ZipFile(zip_path, "r") as z:
                    z.extractall(temp_dir)

                # Find Excel file in extracted contents
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
                    return redirect(
                        "teacher:manage_items",
                        lesson_id=activity.lesson.id,
                        activity_id=activity.id,
                    )

                # Process first Excel file found
                excel_path = os.path.join(temp_dir, excel_files[0])

                # Read Excel file
                df = pd.read_excel(excel_path)

                # Validate required columns
                required_columns = ["title", "question", "answer"]
                for col in required_columns:
                    if col not in df.columns:
                        messages.error(request, f"Missing required column: {col}")
                        return redirect(
                            "teacher:manage_items",
                            activity_id=activity.id,
                        )

                # Create media directory if needed
                media_path = os.path.join("courses", str(course.id), str(activity.id))
                full_media_path = os.path.join(settings.MEDIA_ROOT, media_path)
                os.makedirs(full_media_path, exist_ok=True)

                # Get current max order value from existing items
                current_max_order = (
                    Item.objects.filter(activity=activity).aggregate(Max("order"))[
                        "order__max"
                    ]
                    or 0
                )
                next_order = current_max_order + 1

                # Process each row
                success_count = 0
                for _, row in df.iterrows():
                    try:
                        # Create new exercise item with sequential order
                        item = Item(
                            activity=activity,
                            title=row["title"],
                            question=row["question"],
                            answer=row["answer"],
                            order=next_order,
                        )
                        next_order += 1

                        # Handle image file if exists
                        if "image_filename" in df.columns and pd.notna(
                            row.get("image_filename")
                        ):
                            img_filename = row["image_filename"]
                            img_path = find_file_in_directory(temp_dir, img_filename)
                            if img_path:
                                item.image = save_media_file(
                                    img_path, full_media_path, media_path, img_filename
                                )

                        # Handle audio file if exists
                        if "audio_filename" in df.columns and pd.notna(
                            row.get("audio_filename")
                        ):
                            audio_filename = row["audio_filename"]
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
                    except Exception as e:
                        print(f"Error processing item {row.get('title', '')}: {str(e)}")

                messages.success(
                    request,
                    f"Successfully imported {success_count} out of {len(df)} items",
                )
                return redirect(
                    "teacher:manage_items",
                    activity_id=activity.id,
                )

        except Exception as e:
            messages.error(request, f"Error processing ZIP file: {str(e)}")

    return redirect("teacher:manage_items", activity_id=activity.id)


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
