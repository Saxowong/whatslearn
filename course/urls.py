from django.urls import path
from course import views

app_name = "course"  # Namespace for course-related URLs

urlpatterns = [
    path("<int:course_id>/", views.course_view, name="course"),
    path("enroll/<int:course_id>/", views.enroll_view, name="enroll_course"),
    path(
        "<int:course_id>/unsubscribe/",
        views.unsubscribe_course,
        name="unsubscribe_course",
    ),
    path("activity/<int:activity_id>/", views.activity_view, name="activity_detail"),
    path(
        "submit_activity/<int:activity_id>/",
        views.submit_activity_view,
        name="submit_activity",
    ),
]
