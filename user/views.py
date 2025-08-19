from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from .forms import SinglePasswordRegistrationForm, CustomAuthenticationForm
from django.views.decorators.csrf import csrf_protect


# Create your views here.
def register_view(request):
    if request.method == "POST":
        form = SinglePasswordRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # Log the user in
            # Create a Profile instance for the new user
            return redirect(
                "student_courses"
            )  # Redirect to admin page after registration
    else:
        form = SinglePasswordRegistrationForm()
    return render(request, "user/register.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if not form.cleaned_data.get("remember_me"):
                request.session.set_expiry(0)  # Session expires on browser close
            return redirect(
                "student_courses"
            )  # Redirect to the desired page after login
    else:
        form = CustomAuthenticationForm()
    return render(request, "user/login.html", {"form": form})


@login_required
@csrf_protect
def logout_view(request):
    if request.method == "POST":
        logout(request)
        return redirect("login")
    elif request.method == "GET":
        return redirect("login")
