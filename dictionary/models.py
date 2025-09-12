from django.db import models

class DictionaryItem(models.Model):
    word = models.CharField(max_length=255, unique=True)  # The word to query, unique to avoid duplicates
    meaning = models.TextField()  # The definition or meaning
    # Optional fields: Add more if needed, e.g.,
    # pronunciation = models.CharField(max_length=255, blank=True)
    # example_sentence = models.TextField(blank=True)

    def __str__(self):
        return self.word