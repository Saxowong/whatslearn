from django.contrib import admin
from django import forms
from django.urls import reverse
from django.utils.html import format_html
from django.utils import timezone
from django.shortcuts import redirect
from urllib.parse import parse_qs
from .models import (
    Course,
    Lesson,
    Activity,
    Category,
    Item,
    StudentCourse,
    StudentActivity,
    StudentItem,
)


# Custom form for Activity to handle video_embed_code and pdf_file
class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = "__all__"
        widgets = {
            "video_embed_code": forms.Textarea(attrs={"rows": 4}),
            "html_content": forms.Textarea(attrs={"rows": 4}),
            "pdf_file": forms.FileInput(),
        }

    def clean(self):
        cleaned_data = super().clean()
        activity_type = cleaned_data.get("activity_type")
        pdf_file = cleaned_data.get("pdf_file")
        video_embed_code = cleaned_data.get("video_embed_code")
        html_content = cleaned_data.get("html_content")

        # Validation for pdf_file
        if activity_type == "pdf" and not pdf_file and not self.instance.pdf_file:
            self.add_error("pdf_file", "A PDF file is required for PDF activities.")
        elif activity_type != "pdf" and pdf_file:
            self.add_error("pdf_file", "PDF file should only be uploaded for PDF activities.")

        # Validation for other fields
        if activity_type == "video" and not video_embed_code:
            self.add_error("video_embed_code", "Video embed code is required for Video activities.")
        elif activity_type == "html" and not html_content:
            self.add_error("html_content", "HTML content is required for Content activities.")

        return cleaned_data
# Inline for Lessons within Course
class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1
    fields = ("title", "order")
    readonly_fields = ("created_at", "updated_at")
    list_editable = ("order",)
    show_change_link = True
    ordering = ("order",)
    autocomplete_fields = ("course",)


# Inline for Activities within Lesson
class ActivityInline(admin.TabularInline):
    model = Activity
    extra = 1
    fields = ("title", "activity_type", "order")
    readonly_fields = ("created_at", "updated_at")
    list_editable = ("order",)
    show_change_link = True
    ordering = ("order",)
    autocomplete_fields = ("lesson",)


# Inline for Items within Activity
class ItemInline(admin.TabularInline):
    model = Item
    extra = 1
    fields = ("title", "question", "answer", "order")
    list_editable = ("order",)
    ordering = ("order",)
    autocomplete_fields = ("activity",)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("category_name", "parent_category")
    search_fields = ("category_name", "parent_category__category_name")
    list_filter = ("parent_category",)
    ordering = ("category_name",)
    autocomplete_fields = ("parent_category",)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "teacher",
        "lesson_count",
        "created_at",
        "updated_at",
    )
    search_fields = (
        "title",
        "description",
        "category__category_name",
        "teacher__user__username",
    )
    list_filter = ("category", "teacher", "created_at")
    ordering = ("title", "-created_at")
    inlines = [LessonInline]
    autocomplete_fields = ("category", "teacher")
    readonly_fields = ("created_at", "updated_at")

    def lesson_count(self, obj):
        url = reverse("admin:course_lesson_changelist") + f"?course__id__exact={obj.id}"
        add_url = (
            reverse("admin:course_lesson_add")
            + f"?_changelist_filters=course__id__exact%3D{obj.id}"
        )
        return format_html(
            '<a href="{}">Lessons ({})</a> | <a href="{}" class="addlink">Add Lesson</a>',
            url,
            obj.lessons.count(),
            add_url,
        )

    lesson_count.short_description = "Lessons"

    def save_formset(self, request, form, formset, change):
        super().save_formset(request, form, formset, change)
        if formset.model == Lesson:
            course_id = form.instance.id
            lessons = Lesson.objects.filter(course__id=course_id).order_by(
                "order", "title"
            )
            for index, lesson in enumerate(lessons, start=1):
                if lesson.order != index:
                    lesson.order = index
                    lesson.save()


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "course",
        "order",
        "activity_count",
        "created_at",
        "updated_at",
    )
    search_fields = ("title", "course__title")
    list_filter = ("course", "created_at")
    list_editable = ("order",)
    ordering = ("course", "order", "title")
    inlines = [ActivityInline]
    autocomplete_fields = ("course",)
    readonly_fields = ("created_at", "updated_at")

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj is None:  # Only for add form
            course_id = self._get_course_id_from_request(request)
            if course_id:
                try:
                    course = Course.objects.get(id=course_id)
                    form.base_fields["course"].initial = course
                    form.base_fields["course"].disabled = True
                except Course.DoesNotExist:
                    pass
        return form

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        course_id = self._get_course_id_from_request(request)
        if course_id:
            initial["course"] = course_id
        return initial

    def _get_course_id_from_request(self, request):
        course_id = request.GET.get("course_id")
        if course_id:
            return course_id
        changelist_filters = request.GET.get("_changelist_filters")
        if changelist_filters:
            try:
                filters = parse_qs(changelist_filters)
                course_filter = filters.get("course__id__exact", [None])[0]
                return course_filter
            except (IndexError, AttributeError):
                pass
        return None

    def response_add(self, request, obj, post_url_continue=None):
        if "_addanother" not in request.POST and "_continue" not in request.POST:
            return redirect(
                reverse("admin:course_lesson_changelist")
                + f"?course__id__exact={obj.course.id}"
            )
        return super().response_add(request, obj, post_url_continue)

    def activity_count(self, obj):
        url = (
            reverse("admin:course_activity_changelist") + f"?lesson__id__exact={obj.id}"
        )
        return format_html(
            '<a href="{}">Activities ({})</a>', url, obj.activities.count()
        )

    activity_count.short_description = "Activities"

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        course_id = form.instance.course_id if change else None
        if course_id:
            lessons = Lesson.objects.filter(course__id=course_id).order_by(
                "order", "title"
            )
            for index, lesson in enumerate(lessons, start=1):
                if lesson.order != index:
                    lesson.order = index
                    lesson.save()

    def save_formset(self, request, form, formset, change):
        super().save_formset(request, form, formset, change)
        if formset.model == Activity:
            lesson_id = form.instance.id
            activities = Activity.objects.filter(lesson__id=lesson_id).order_by(
                "order", "title"
            )
            for index, activity in enumerate(activities, start=1):
                if activity.order != index:
                    activity.order = index
                    activity.save()


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    form = ActivityForm
    list_display = (
        "title",
        "lesson",
        "activity_type",
        "order",
        "item_count",
        "pdf_file_link",
        "created_at",
        "updated_at",
    )
    search_fields = ("title", "lesson__title", "lesson__course__title")
    list_filter = ("activity_type", "lesson", "lesson__course", "created_at")
    list_editable = (
        "lesson",
        "order",
    )
    ordering = ("lesson", "order", "title")
    inlines = [ItemInline]
    autocomplete_fields = ("lesson",)
    readonly_fields = ("created_at", "updated_at")

    def pdf_file_link(self, obj):
        if obj.activity_type == "pdf" and obj.pdf_file:
            return format_html('<a href="{}" target="_blank">View PDF</a>', obj.pdf_file.url)
        return "-"
    pdf_file_link.short_description = "PDF File"
    pdf_file_link.allow_tags = True

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj is None:  # Only for add form
            lesson_id = self._get_lesson_id_from_request(request)
            if lesson_id:
                try:
                    lesson = Lesson.objects.get(id=lesson_id)
                    form.base_fields["lesson"].initial = lesson
                    form.base_fields["lesson"].disabled = True
                except Lesson.DoesNotExist:
                    pass
        return form

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        lesson_id = self._get_lesson_id_from_request(request)
        if lesson_id:
            initial["lesson"] = lesson_id
        return initial

    def _get_lesson_id_from_request(self, request):
        lesson_id = request.GET.get("lesson_id")
        if lesson_id:
            return lesson_id
        changelist_filters = request.GET.get("_changelist_filters")
        if changelist_filters:
            try:
                filters = parse_qs(changelist_filters)
                lesson_filter = filters.get("lesson__id__exact", [None])[0]
                return lesson_filter
            except (IndexError, AttributeError):
                pass
        return None

    def response_add(self, request, obj, post_url_continue=None):
        if "_addanother" not in request.POST and "_continue" not in request.POST:
            return redirect(
                reverse("admin:course_activity_changelist")
                + f"?lesson__id__exact={obj.lesson.id}"
            )
        return super().response_add(request, obj, post_url_continue)

    def item_count(self, obj):
        url = reverse("admin:course_item_changelist") + f"?activity__id__exact={obj.id}"
        return format_html('<a href="{}">Items ({})</a>', url, obj.items.count())
    item_count.short_description = "Items"
    item_count.allow_tags = True

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        lesson_id = form.instance.lesson_id if change else None
        if lesson_id:
            activities = Activity.objects.filter(lesson__id=lesson_id).order_by(
                "order", "title"
            )
            for index, activity in enumerate(activities, start=1):
                if activity.order != index:
                    activity.order = index
                    activity.save()

    def save_formset(self, request, form, formset, change):
        super().save_formset(request, form, formset, change)
        if formset.model == Item:
            activity_id = form.instance.id
            items = Item.objects.filter(activity__id=activity_id).order_by(
                "order", "title"
            )
            for index, item in enumerate(items, start=1):
                if item.order != index:
                    item.order = index
                    item.save()
@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("title", "activity", "question", "answer", "number_answers", "order")
    search_fields = (
        "title",
        "question",
        "answer",
        "activity__title",
        "activity__lesson__title",
    )
    list_filter = ("activity", "activity__lesson", "activity__lesson__course")
    list_editable = ("order",)
    ordering = ("activity", "order", "title")
    autocomplete_fields = ("activity",)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj is None:  # Only for add form
            activity_id = self._get_activity_id_from_request(request)
            if activity_id:
                try:
                    activity = Activity.objects.get(id=activity_id)
                    form.base_fields["activity"].initial = activity
                    form.base_fields["activity"].disabled = True
                except Activity.DoesNotExist:
                    pass
        return form

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        activity_id = self._get_activity_id_from_request(request)
        if activity_id:
            initial["activity"] = activity_id
        return initial

    def _get_activity_id_from_request(self, request):
        activity_id = request.GET.get("activity_id")
        if activity_id:
            return activity_id
        changelist_filters = request.GET.get("_changelist_filters")
        if changelist_filters:
            try:
                filters = parse_qs(changelist_filters)
                activity_filter = filters.get("activity__id__exact", [None])[0]
                return activity_filter
            except (IndexError, AttributeError):
                pass
        return None

    def response_add(self, request, obj, post_url_continue=None):
        if "_addanother" not in request.POST and "_continue" not in request.POST:
            return redirect(
                reverse("admin:course_item_changelist")
                + f"?activity__id__exact={obj.activity.id}"
            )
        return super().response_add(request, obj, post_url_continue)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        activity_id = form.instance.activity_id if change else None
        if activity_id:
            items = Item.objects.filter(activity__id=activity_id).order_by(
                "order", "title"
            )
            for index, item in enumerate(items, start=1):
                if item.order != index:
                    item.order = index
                    item.save()


@admin.register(StudentCourse)
class StudentCourseAdmin(admin.ModelAdmin):
    list_display = ("student", "course", "enrolled_at")
    search_fields = ("student__user__username", "course__title")
    list_filter = ("course", "student", "enrolled_at")
    readonly_fields = ("enrolled_at", "updated_at")
    autocomplete_fields = ("student", "course")
    actions = ["mark_enrolled"]

    def mark_enrolled(self, request, queryset):
        queryset.update(enrolled_at=timezone.now())
        self.message_user(request, "Selected student courses marked as enrolled.")

    mark_enrolled.short_description = "Mark selected courses as enrolled"


@admin.register(StudentActivity)
class StudentActivityAdmin(admin.ModelAdmin):
    list_display = ("student", "activity", "progress", "completed", "updated_at")
    search_fields = (
        "student__user__username",
        "activity__title",
        "activity__lesson__title",
    )
    list_filter = ("activity", "activity__lesson", "student", "completed", "updated_at")
    readonly_fields = ("updated_at",)
    autocomplete_fields = ("student", "activity")
    actions = ["mark_completed", "reset_progress"]

    def mark_completed(self, request, queryset):
        queryset.update(completed=True, progress=100)
        self.message_user(request, "Selected student activities marked as completed.")

    mark_completed.short_description = "Mark selected activities as completed"

    def reset_progress(self, request, queryset):
        queryset.update(progress=0, completed=False)
        self.message_user(request, "Progress reset for selected student activities.")

    reset_progress.short_description = "Reset progress for selected activities"


@admin.register(StudentItem)
class StudentItemAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "item",
        "successes",
        "is_master",
        "start_at",
        "updated_at",
        "next_1",
        "next_2",
        "revise_at",
        "continue_revision",
    )
    search_fields = ("student__user__username", "item__title", "item__activity__title")
    list_filter = ("item", "item__activity", "student", "is_master", "start_at")
    readonly_fields = ("start_at", "updated_at")
    autocomplete_fields = ("student", "item")
    actions = ["mark_mastered", "reset_successes"]

    def mark_mastered(self, request, queryset):
        default_successes = 1
        queryset.update(is_master=True, successes=default_successes)
        self.message_user(request, "Selected student items marked as mastered.")

    mark_mastered.short_description = "Mark selected items as mastered"

    def reset_successes(self, request, queryset):
        queryset.update(successes=0, is_master=False)
        self.message_user(request, "Successes reset for selected student items.")

    reset_successes.short_description = "Reset successes for selected items"
