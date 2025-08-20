from django import forms
from course.models import Course, Lesson, Activity, Item
from django.core.validators import FileExtensionValidator

import re # For regex operations

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
        fields = [
            "title",
            "item_type",
            "question",
            "answer",
            "answer1",
            "answer2",
            "answer3",
            "answer4",
            "image",
            "audio",
            "order",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "required": True}),
            "item_type": forms.Select(attrs={"class": "form-control", "required": True}),
            "question": forms.Textarea(
                attrs={"class": "form-control", "rows": 4, "required": True}
            ),
            "answer": forms.TextInput(
                attrs={"class": "form-control", "required": False}
            ),
            "answer1": forms.TextInput(
                attrs={"class": "form-control", "required": False}
            ),
            "answer2": forms.TextInput(
                attrs={"class": "form-control", "required": False}
            ),
            "answer3": forms.TextInput(
                attrs={"class": "form-control", "required": False}
            ),
            "answer4": forms.TextInput(
                attrs={"class": "form-control", "required": False}
            ),
            "image": forms.FileInput(
                attrs={"class": "form-control", "accept": "image/*"}
            ),
            "audio": forms.FileInput(
                attrs={"class": "form-control", "accept": "audio/mp3,audio/wav,audio/ogg,audio/m4a"}
            ),
            "order": forms.NumberInput(
                attrs={"class": "form-control", "min": 0, "required": True}
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        item_type = cleaned_data.get("item_type")
        question = cleaned_data.get("question")
        answer = cleaned_data.get("answer")
        answer1 = cleaned_data.get("answer1")
        answer2 = cleaned_data.get("answer2")
        answer3 = cleaned_data.get("answer3")
        answer4 = cleaned_data.get("answer4")

        if item_type == "card":
            # Flash Card: requires question and answer
            if not answer:
                self.add_error("answer", "Answer is required for Flash Card items.")
        elif item_type == "mc":
            # Multiple Choice: requires question, answer, and all four answer fields
            if not answer:
                self.add_error("answer", "Correct answer is required for Multiple Choice items.")
            if not answer1:
                self.add_error("answer1", "Answer 1 is required for Multiple Choice items.")
            if not answer2:
                self.add_error("answer2", "Answer 2 is required for Multiple Choice items.")
            if not answer3:
                self.add_error("answer3", "Answer 3 is required for Multiple Choice items.")
            if not answer4:
                self.add_error("answer4", "Answer 4 is required for Multiple Choice items.")
        elif item_type == "blank":
            # Fill in the Blank: requires answer1 to answer4 based on number of _____ in question
            if question:
                blank_count = len(re.findall(r"_{5,}", question))  # Count sequences of 5+ underscores
                if blank_count == 0:
                    self.add_error("question", "Fill in the Blank questions must contain at least one '_____' placeholder.")
                if blank_count >= 1 and not answer1:
                    self.add_error("answer1", "Answer 1 is required for Fill in the Blank items.")
                if blank_count >= 2 and not answer2:
                    self.add_error("answer2", "Answer 2 is required for Fill in the Blank items.")
                if blank_count >= 3 and not answer3:
                    self.add_error("answer3", "Answer 3 is required for Fill in the Blank items.")
                if blank_count >= 4 and not answer4:
                    self.add_error("answer4", "Answer 4 is required for Fill in the Blank items.")
            else:
                self.add_error("question", "Question is required for Fill in the Blank items.")

        return cleaned_data
class ItemImportForm(forms.Form):
    zip_file = forms.FileField(
        label="ZIP File",
        validators=[FileExtensionValidator(allowed_extensions=["zip"])],
        help_text="Upload a ZIP file containing one CSV file (with column titles: title, question, answer, image_filename, audio_filename) and optional image (JPG/PNG) and audio (MP3) files.",
    )
