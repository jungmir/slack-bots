"""Django admin configuration for announcements."""
from django.contrib import admin
from django.db import models
from django.db.models import Count
from django_json_widget.widgets import JSONEditorWidget
from .models import Announcement, ReadReceipt, BlockKitTemplate


class ReadReceiptInline(admin.TabularInline):
    """Inline admin for read receipts."""
    model = ReadReceipt
    extra = 0
    readonly_fields = ['user_id', 'user_name', 'confirmed_at']
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    """Admin interface for announcements."""

    list_display = [
        'title',
        'channel_name',
        'sender_id',
        'created_at',
        'get_read_count'
    ]
    list_filter = ['channel_name', 'created_at']
    search_fields = ['title', 'content', 'channel_name']
    readonly_fields = ['message_ts', 'created_at', 'get_read_count']
    inlines = [ReadReceiptInline]

    fieldsets = (
        ('기본 정보', {
            'fields': ('title', 'content')
        }),
        ('채널 정보', {
            'fields': ('channel_id', 'channel_name')
        }),
        ('발송 정보', {
            'fields': ('sender_id', 'message_ts', 'created_at', 'get_read_count')
        }),
    )

    def get_read_count(self, obj):
        """Get read count for list display."""
        return obj.read_count
    get_read_count.short_description = '읽음 수'

    def get_queryset(self, request):
        """Optimize queryset with read count."""
        qs = super().get_queryset(request)
        return qs.annotate(
            _read_count=Count('read_receipts')
        )


@admin.register(ReadReceipt)
class ReadReceiptAdmin(admin.ModelAdmin):
    """Admin interface for read receipts."""

    list_display = ['user_name', 'announcement', 'confirmed_at']
    list_filter = ['confirmed_at']
    search_fields = ['user_name', 'announcement__title']
    readonly_fields = ['announcement', 'user_id', 'user_name', 'confirmed_at']

    def has_add_permission(self, request):
        return False


@admin.register(BlockKitTemplate)
class BlockKitTemplateAdmin(admin.ModelAdmin):
    """Admin interface for Block Kit templates with JSON editor."""

    list_display = [
        'name',
        'template_type',
        'is_active',
        'updated_at'
    ]
    list_filter = ['template_type', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('기본 정보', {
            'fields': ('name', 'template_type', 'description', 'is_active')
        }),
        ('Block Kit JSON', {
            'fields': ('blocks',),
            'description': '아래에서 Slack Block Kit JSON을 편집할 수 있습니다. '
                         '<a href="https://app.slack.com/block-kit-builder" target="_blank">'
                         'Block Kit Builder</a>에서 미리 구성한 후 복사할 수 있습니다.'
        }),
        ('메타데이터', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    formfield_overrides = {
        # Use JSON editor widget for blocks field
        models.JSONField: {'widget': JSONEditorWidget},
    }

    def save_model(self, request, obj, form, change):
        """Save model with validation."""
        # You can add JSON validation here if needed
        super().save_model(request, obj, form, change)


# Customize admin site headers
admin.site.site_header = 'NotiPy 관리'
admin.site.site_title = 'NotiPy'
admin.site.index_title = '슬랙 봇 관리'
