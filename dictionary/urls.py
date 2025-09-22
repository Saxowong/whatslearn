from django.urls import path
from .views import dictionary_search
from dictionary import views

app_name = "dictionary"  # Namespace for dictionary-related URLs

urlpatterns = [
    path("", dictionary_search, name="dictionary_search"),  # e.g., /dictionary/
]
