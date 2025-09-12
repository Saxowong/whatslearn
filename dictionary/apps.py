from django.apps import AppConfig


class DictionaryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dictionary'
    
    def ready(self):
            # Optional: Import signals if you add them later (e.g., in dictionary/signals.py)
            # import dictionary.signals  # Uncomment and create signals.py if needed
            pass  # Placeholder for now