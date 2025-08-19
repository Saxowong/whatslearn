from django import forms
from course.models import Course, Lesson, Activity, Item
from django.core.validators import FileExtensionValidator


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = [
            "title",
            "category",
            "image",
            "video",
            "is_published",
            "description",
        ]  # Fix: is_published
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "is_published": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),  # Fix: is_published
            "image": forms.FileInput(attrs={"class": "form-control"}),
            "video": forms.FileInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(
                attrs={"class": "form-control tinymce-editor"}
            ),
        }


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = [
            "title",
            "order",
        ]  # Fix: is_published
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "order": forms.NumberInput(attrs={"class": "form-control"}),
        }


class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ["activity_type", "title", "html_content", "video_embed_code", "order"]
        widgets = {
            "activity_type": forms.Select(),
            "title": forms.TextInput(attrs={"class": "form-control", "required": True}),
            "html_content": forms.Textarea(attrs={"class": "form-control ckeditor"}),
            "video_embed_code": forms.Textarea(
                attrs={"class": "form-control", "rows": 4}
            ),
            "order": forms.NumberInput(attrs={"class": "form-control", "min": -1}),
        }


class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ["title", "question", "answer", "image", "audio", "order"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "required": True}),
            "question": forms.Textarea(
                attrs={"class": "form-control", "rows": 4, "required": True}
            ),
            "answer": forms.TextInput(
                attrs={"class": "form-control", "required": True}
            ),
            "image": forms.FileInput(
                attrs={"class": "form-control", "accept": "image/*"}
            ),
            "audio": forms.FileInput(
                attrs={"class": "form-control", "accept": "audio/*"}
            ),
            "order": forms.NumberInput(
                attrs={"class": "form-control", "min": 0, "required": True}
            ),
        }


class ItemImportForm(forms.Form):
    zip_file = forms.FileField(
        label="ZIP File",
        validators=[FileExtensionValidator(allowed_extensions=["zip"])],
        help_text="Upload a ZIP file containing one CSV file (with column titles: title, question, answer, image_filename, audio_filename) and optional image (JPG/PNG) and audio (MP3) files.",
    )
