"""
URL configuration for whatslearn project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.shortcuts import redirect
from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from user import views
from django.contrib.auth import (
    views as authentication_views,
)  # auth_views is a module that provides views for authentication
from django.conf.urls.static import static
from django.views.static import serve
from user.views import logout_view, login_view

from course.views import (
    UserProfileAPIView,
    ProfileByUserIDAPIView,
    UserEnrolledCoursesAPIView,
    student_course_view,
    revision_view,
    submit_revision,
    available_courses_view,
    enroll_view,
)


def redirect_based_on_auth(request, invalid_path):
    # Skip media URLs to let static() handle them
    if invalid_path.startswith(settings.MEDIA_URL.lstrip("/")):
        relative_path = invalid_path[len(settings.MEDIA_URL.lstrip("/")):]
        return serve(request, path=relative_path, document_root=settings.MEDIA_ROOT)
    # Skip static URLs to let Nginx handle them
    if invalid_path.startswith(settings.STATIC_URL.lstrip("/")):
        relative_path = invalid_path[len(settings.STATIC_URL.lstrip("/")):]
        return serve(request, path=relative_path, document_root=settings.STATIC_ROOT)
    # Redirect based on authentication
    if request.user.is_authenticated:
        return redirect("student_courses")
    return redirect("login")

urlpatterns = [
    path("", lambda request: redirect("student_courses"), name="home"),
    path("admin", admin.site.urls),
    path("register", views.register_view, name="register"),
    path("dictionary/", include("dictionary.urls")),
    path("logout", logout_view, name="logout"),
    path("login", login_view, name="login"),
    path("course/", include("course.urls")),  # Updated to course.urls
    path("manage/", include("teacher.urls")),
    path("courses", student_course_view, name="student_courses"),
    path("courses/available", available_courses_view, name="available_courses"),
    path("revision/<int:course_id>", revision_view, name="revision"),
    path(
        "revision/submit/<int:course_id>",
        submit_revision,
        name="submit_revision",
    ),
    # Catch-all pattern to redirect based on authentication status
    path("<path:invalid_path>", redirect_based_on_auth, name="redirect_invalid"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
