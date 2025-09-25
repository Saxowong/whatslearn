from django.db import models
from django.utils import timezone
from user.models import Profile


class DictionaryItem(models.Model):
    word = models.CharField(max_length=255, unique=True)
    meaning = models.TextField()

    def __str__(self):
        return self.word


class StudentWord(models.Model):
    student = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="student_words"
    )
    dictionary_item = models.ForeignKey(
        DictionaryItem, on_delete=models.CASCADE, null=True
    )
    word = models.CharField(max_length=255)  # Remove unique=True and default
    meaning = models.TextField(blank=True, null=True)
    start_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)
    successes = models.SmallIntegerField(default=0)
    is_master = models.BooleanField(default=False)
    next_1 = models.IntegerField(default=1)
    next_2 = models.IntegerField(default=1)
    revise_at = models.DateTimeField(blank=True, null=True)
    continue_revision = models.BooleanField(default=True)

    class Meta:
        unique_together = ("student", "word")

    def __str__(self):
        return (
            f"{self.student.user.username} engaged in {self.word}"  # Fixed: self.word
        )

    def save(self, *args, **kwargs):
        # Auto-populate word and meaning from dictionary_item
        if self.dictionary_item:
            self.word = self.dictionary_item.word
            self.meaning = self.dictionary_item.meaning
        super().save(*args, **kwargs)
