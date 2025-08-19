# users/admin.py
from django.contrib import admin
from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "name",
        "picture",
    )  # Add fields to display in the list view
    search_fields = ("user__username", "name")  # Enable search by username

    # Optionally, you can customize the form layout
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "user",
                    "name",
                    "picture",
                )
            },
        ),
    )  # Add other fields as needed
