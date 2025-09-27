from django.core.management.base import BaseCommand
from dictionary.models import DictionaryItem


class Command(BaseCommand):
    help = "Lists and optionally deletes DictionaryItem entries with multiple words"

    def add_arguments(self, parser):
        parser.add_argument(
            "--delete",
            action="store_true",
            help="Delete multi-word DictionaryItem entries (default: list only)",
        )

    def handle(self, *args, **options):
        # Find DictionaryItem entries with spaces in the word field
        multiword_items = DictionaryItem.objects.filter(word__contains=" ")

        if not multiword_items.exists():
            self.stdout.write(
                self.style.SUCCESS("No multi-word DictionaryItem entries found.")
            )
            return

        self.stdout.write(
            f"Found {multiword_items.count()} multi-word DictionaryItem entries:"
        )
        for item in multiword_items:
            self.stdout.write(f"- {item.word} (ID: {item.id}, Meaning: {item.meaning})")

        if options["delete"]:
            # Count associated StudentWord entries
            student_word_count = 0
            for item in multiword_items:
                student_word_count += item.studentword_set.count()

            self.stdout.write(
                self.style.WARNING(
                    f"\nDeleting {multiword_items.count()} DictionaryItem entries "
                    f"and {student_word_count} associated StudentWord entries..."
                )
            )

            # Delete the items (StudentWord entries are deleted automatically via CASCADE)
            deleted_count = multiword_items.delete()[0]
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully deleted {deleted_count} DictionaryItem entries."
                )
            )
        else:
            self.stdout.write(
                self.style.NOTICE(
                    "To delete these entries, run the command with --delete."
                )
            )
