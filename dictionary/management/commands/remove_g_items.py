from django.core.management.base import BaseCommand
from dictionary.models import DictionaryItem


class Command(BaseCommand):
    help = "Lists and optionally deletes DictionaryItem entries starting with g or G"

    def add_arguments(self, parser):
        parser.add_argument(
            "--delete",
            action="store_true",
            help="Delete DictionaryItem entries starting with g or G (default: list only)",
        )

    def handle(self, *args, **options):
        # Find DictionaryItem entries starting with g or G
        g_items = DictionaryItem.objects.filter(word__istartswith="g")

        if not g_items.exists():
            self.stdout.write(
                self.style.SUCCESS(
                    "No DictionaryItem entries starting with g or G found."
                )
            )
            return

        self.stdout.write(
            f"Found {g_items.count()} DictionaryItem entries starting with g or G:"
        )
        for item in g_items:
            self.stdout.write(f"- {item.word} (ID: {item.id}, Meaning: {item.meaning})")

        if options["delete"]:
            # Count associated StudentWord entries
            student_word_count = 0
            for item in g_items:
                student_word_count += item.studentword_set.count()

            self.stdout.write(
                self.style.WARNING(
                    f"\nDeleting {g_items.count()} DictionaryItem entries "
                    f"and {student_word_count} associated StudentWord entries..."
                )
            )

            # Delete the items (StudentWord entries are deleted automatically via CASCADE)
            deleted_count = g_items.delete()[0]
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
