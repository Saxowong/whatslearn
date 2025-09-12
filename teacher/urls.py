from django.urls import path
from . import views  # Import from courses app since teacher_courses is there


app_name = "teacher"

urlpatterns = [
    path('course/<int:course_id>/learners/', views.manage_learners, name="manage_learners"),
    path("courses", views.manage_courses, name="manage_courses"),
    path("edit-course/<int:course_id>", views.edit_course, name="edit_course"),
    path("delete-course/<int:course_id>", views.delete_course, name="delete_course"),
    path("course/<int:course_id>", views.manage_lessons, name="manage_lessons"),
    path("edit-lesson/<int:lesson_id>", views.edit_lesson, name="edit_lesson"),
    path("delete-lesson/<int:lesson_id>", views.delete_lesson, name="delete_lesson"),
    path("lesson/<int:lesson_id>", views.manage_activities, name="manage_activities"),
    path(
        "edit-activity/<int:lesson_id>/<int:activity_id>",
        views.edit_activity,
        name="edit_activity",
    ),
    path(
        "delete-activity/<int:activity_id>",
        views.delete_activity,
        name="delete_activity",
    ),
    path(
        "activity/<int:activity_id>",
        views.manage_items,
        name="manage_items",
    ),
    path(
        "edit-item/<int:activity_id>/<int:item_id>",
        views.edit_item,
        name="edit_item",
    ),
    path(
        "delete-item/<int:item_id>",
        views.delete_item,
        name="delete_item",
    ),
    path("import-items/<int:activity_id>", views.import_items, name="import_items"),
]
