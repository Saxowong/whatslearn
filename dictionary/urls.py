from django.urls import path
from .views import dictionary_search
from dictionary import views

app_name = "dictionary"  # Namespace for dictionary-related URLs

urlpatterns = [
    path("", dictionary_search, name="dictionary_search"),  # e.g., /dictionary/
    path("save-word/", views.save_word, name="save_word"),
    path("revision/", views.dictionary_revision, name="dictionary_revision"),
    path(
        "revision/submit/",
        views.dictionary_revision_submit,
        name="dictionary_revision_submit",
    ),
]
