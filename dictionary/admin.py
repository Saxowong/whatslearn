from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportMixin
from .models import DictionaryItem, StudentWord
from import_export.fields import Field


class DictionaryItemResource(resources.ModelResource):
    class Meta:
        model = DictionaryItem
        fields = ("word", "meaning")
        import_id_fields = ("word",)
        exclude = ("id",)


class StudentWordResource(resources.ModelResource):
    student_username = Field()
    dictionary_word = Field()

    class Meta:
        model = StudentWord
        fields = (
            "student_username",
            "word",
            "dictionary_word",
            "successes",
            "is_master",
            "start_at",
            "revise_at",
            "continue_revision",
        )
        export_order = fields

    def dehydrate_student_username(self, student_word):
        return student_word.student.user.username

    def dehydrate_dictionary_word(self, student_word):
        return student_word.dictionary_item.word


@admin.register(StudentWord)
class StudentWordAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = StudentWordResource
    list_display = (
        "student_username",
        "word",
        "meaning",
        "successes",
        "is_master",
        "start_at",
        "revise_at",
        "continue_revision",
    )
    list_filter = (
        "is_master",
        "continue_revision",
        "start_at",
        "revise_at",
        "student__user__username",
    )
    search_fields = (
        "word",
        "meaning",
        "student__user__username",
        "dictionary_item__word",
    )
    readonly_fields = ("start_at", "updated_at")
    list_per_page = 20

    def student_username(self, obj):
        return obj.student.user.username

    student_username.short_description = "Student"
    student_username.admin_order_field = "student__user__username"

    def dictionary_reference(self, obj):
        return obj.dictionary_item.word

    dictionary_reference.short_description = "Dictionary Reference"
    dictionary_reference.admin_order_field = "dictionary_item__word"

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if obj:  # Editing an existing object
            readonly_fields.extend(["word", "meaning", "dictionary_item"])
        return readonly_fields

    def save_model(self, request, obj, form, change):
        if obj.dictionary_item and (not obj.word or not obj.meaning):
            if not obj.word:
                obj.word = obj.dictionary_item.word
            if not obj.meaning:
                obj.meaning = obj.dictionary_item.meaning
        super().save_model(request, obj, form, change)


@admin.register(DictionaryItem)
class DictionaryItemAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = DictionaryItemResource
    list_display = ("word", "meaning", "student_word_count")
    search_fields = ("word",)

    def student_word_count(self, obj):
        return obj.student_words.count()

    student_word_count.short_description = "Students Learning"
