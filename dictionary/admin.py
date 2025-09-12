from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportMixin
from .models import DictionaryItem
from import_export.fields import Field  # Optional, for custom mappings if needed

class DictionaryItemResource(resources.ModelResource):
    class Meta:
        model = DictionaryItem
        fields = ('word', 'meaning')  # Explicitly include only importable fields
        import_id_fields = ('word',)  # Use 'word' (unique) to identify records instead of 'id'
        exclude = ('id',)  # Exclude the auto-generated ID from import/export

@admin.register(DictionaryItem)
class DictionaryItemAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = DictionaryItemResource
    list_display = ('word', 'meaning')
    search_fields = ('word',)