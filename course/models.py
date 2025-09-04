from django.db import models
from user.models import Profile
from tinymce.models import HTMLField
from django.core.files.base import ContentFile
from PIL import Image as PilImage
from django.core.validators import FileExtensionValidator

# First, create a custom aggregation (put this in your models.py or aggregations.py)
from django.db.models import Aggregate
import io, os


def course_media_path(instance, filename):
    """Upload path: media/courses/{course_id}/{filename}"""
    # Extract the base filename to avoid duplicating the path
    base_filename = os.path.basename(filename)
    return f"courses/{instance.id}/{base_filename}"

def pdf_media_path(instance, filename):
    """Upload path: media/courses/{course_id}/{filename}"""
    base_filename = os.path.basename(filename)
    return f"courses/{instance.lesson.course.id}/{base_filename}"

def item_media_path(instance, filename):
    """Upload path: media/courses/{course_id}/..."""
    # Extract the base filename to avoid duplicating the path
    base_filename = os.path.basename(filename)
    return f"courses/{instance.activity.lesson.course.id}/{base_filename}"



class Category(models.Model):
    category_name = models.CharField(max_length=255)
    parent_category = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="subcategories",
    )

    def __str__(self):
        return self.category_name


class Course(models.Model):
    title = models.CharField(max_length=255)
    image = models.ImageField(
        upload_to=course_media_path,
        blank=True,
        null=True,
        default="default/course-image.jpg",
    )
    is_published = models.BooleanField(default=False)
    teacher = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="courses",
        null=True,
        blank=True,
    )
    video = models.FileField(upload_to=course_media_path, blank=True, null=True)
    description = HTMLField(default="", blank=True, null=True)

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="courses",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.image:
            img = PilImage.open(self.image)

            # Convert image to RGB if it's in RGBA mode
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            img = img.resize((240, 160), PilImage.LANCZOS)  # Resize to 300x300 pixels

            img_io = io.BytesIO()
            img.save(img_io, format="JPEG", quality=85)  # Save as JPEG with quality 85
            img_file = ContentFile(img_io.getvalue(), name=self.image.name)
            self.image = img_file
        super().save(*args, **kwargs)


class Lesson(models.Model):
    title = models.CharField(max_length=255)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="lessons")
    order = models.PositiveIntegerField(
        default=0
    )  # To keep track of the order of lessons
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class Activity(models.Model):
    ACTIVITY_TYPES = [
        ("exercise", "Exercise"),
        ("video", "Video"),
        ("html", "Content"),
        ("pdf", "PDF"),
    ]
    title = models.CharField(max_length=255)
    lesson = models.ForeignKey("Lesson", on_delete=models.CASCADE, related_name="activities")
    activity_type = models.CharField(max_length=10, choices=ACTIVITY_TYPES)
    order = models.IntegerField(default=0)
    html_content = models.TextField(blank=True, null=True)
    video_embed_code = models.TextField(blank=True, null=True)
    pdf_file = models.FileField(upload_to=pdf_media_path, blank=True, null=True, help_text="Upload a PDF file")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class Item(models.Model):
    ITEM_TYPES = [
        ("card", "Flash Card"),
        ("mc", "Multiple Choice"),
        ("blank", "Fill in the Blank"),
    ]
    PLAY_AUDIO = [
        ("start", "Play at Start"),
        ("end", "Play at End"),
        ("both", "Play at Both"),
    ]
    item_type = models.CharField(max_length=10, choices=ITEM_TYPES, default="card")
    item_category = models.CharField(max_length=20, blank=True, null=True) 
    title = models.CharField(max_length=100)  # Title of the activity item
    question = models.TextField()  # Question associated with the activity item
    activity = models.ForeignKey(
        Activity, on_delete=models.CASCADE, related_name="items"
    )
    order = models.PositiveIntegerField(
        default=0
    )  # To keep track of the order of items
    image = models.ImageField(upload_to=item_media_path, blank=True, null=True)
    audio = models.FileField(upload_to=item_media_path, blank=True, null=True, validators=[FileExtensionValidator(allowed_extensions=['mp3', 'wav', 'ogg', 'm4a'])])
    audio_play = models.CharField(max_length=6, choices=PLAY_AUDIO, default="start", null=True, blank=True)
    number_answers = models.SmallIntegerField(default=1, blank=True, null=True)  # Number of answers for MCQ
    answer = models.CharField(max_length=100, blank=True, null=True) 
    answer1 = models.CharField(max_length=100, blank=True, null=True)   # Answer to the question
    answer2 = models.CharField(max_length=100, blank=True, null=True)  # Answer to the question
    answer3 = models.CharField(max_length=100, blank=True, null=True)  # Answer to the question
    answer4 = models.CharField(max_length=100, blank=True, null=True)  # Answer to the question

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class StudentCourse(models.Model):
    student = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="student_courses"
    )
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="student_courses"
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (
            "student",
            "course",
        )  # Ensure a student can enroll in a course only once

    def __str__(self):
        return f"{self.student.user.username} enrolled in {self.course.title}"


class StudentActivity(models.Model):
    student = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="student_activities"
    )
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    updated_at = models.DateTimeField(auto_now=True)
    progress = models.FloatField(default=0, blank=True, null=True)
    completed = models.BooleanField(
        default=False
    )  # To track if the activity is completed


class StudentItem(models.Model):
    student = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="student_items"
    )
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    start_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)
    successes = models.SmallIntegerField(default=0)  # Number of successes
    is_master = models.BooleanField(default=False)
    next_1 = models.IntegerField(default=1)
    next_2 = models.IntegerField(default=1)
    revise_at = models.DateTimeField(blank=True, null=True)
    continue_revision = models.BooleanField(default=True)

    class Meta:
        unique_together = (
            "student",
            "item",
        )  # Ensure a student can enroll in a course only once

    def __str__(self):
        return f"{self.student.user.username} engaged in {self.item.title}"


class GroupConcat(Aggregate):
    function = "GROUP_CONCAT"
    template = '%(function)s(%(distinct)s%(expressions)s SEPARATOR "%(separator)s")'

    def __init__(self, expression, distinct=False, separator=",", **extra):
        super().__init__(
            expression,
            distinct="DISTINCT " if distinct else "",
            separator=separator,
            **extra,
        )

    def convert_value(self, value, expression, connection):
        return value.split(connection.features.group_concat_separator) if value else []
