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
        fields = ['title', 'item_type', 'item_category', 'question', 'number_answers', 'answer','answer1', 'answer2', 'answer3', 'answer4', 'image', 'audio', 'audio_play', 'order']
        widgets = {
            'question': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set required=False for fields that are optional
        self.fields['number_answers'].required = False
        self.fields['answer'].required = False
        self.fields['answer1'].required = False
        self.fields['answer2'].required = False
        self.fields['answer3'].required = False
        self.fields['answer4'].required = False
        self.fields['image'].required = False
        self.fields['audio'].required = False
        self.fields['audio_play'].required = False
        self.fields['order'].required = False

    def clean(self):
        cleaned_data = super().clean()
        item_type = cleaned_data.get('item_type')
        question = cleaned_data.get('question')
        if item_type == 'blank':
            blank_count = len(re.findall(r"___", question)) if question else 0
            if blank_count == 0:
                self.add_error('question', "Fill in the Blank questions must contain at least one '___' placeholder.")
            for i in range(1, min(blank_count + 1, 5)):
                if not cleaned_data.get(f'answer{i}'):
                    self.add_error(f'answer{i}', 'This field is required.')
        elif item_type == 'mc':
            for field in ['answer', 'answer1', 'answer2', 'answer3', 'answer4']:
                if not cleaned_data.get(field):
                    self.add_error(field, 'This field is required.')
        return cleaned_data

class ItemImportForm(forms.Form):
    zip_file = forms.FileField(
        label="ZIP File",
        validators=[FileExtensionValidator(allowed_extensions=["zip"])],
        help_text="Upload a ZIP file containing one CSV file (with column titles: title, question, answer, image_filename, audio_filename) and optional image (JPG/PNG) and audio (MP3) files.",
    )
