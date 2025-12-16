"""Django models for announcements and read receipts."""
from django.db import models
from django.utils import timezone


class Announcement(models.Model):
    """Model for storing announcements."""

    channel_id = models.CharField(max_length=50)
    channel_name = models.CharField(max_length=100)
    title = models.CharField(max_length=200)
    content = models.TextField()
    sender_id = models.CharField(max_length=50)
    message_ts = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        verbose_name = '공지사항'
        verbose_name_plural = '공지사항 목록'

    def __str__(self):
        return f"{self.title} - #{self.channel_name}"

    @property
    def read_count(self):
        """Get count of users who confirmed reading."""
        return self.read_receipts.count()


class ReadReceipt(models.Model):
    """Model for tracking read receipts."""

    announcement = models.ForeignKey(
        Announcement,
        on_delete=models.CASCADE,
        related_name='read_receipts'
    )
    user_id = models.CharField(max_length=50)
    user_name = models.CharField(max_length=100)
    confirmed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [['announcement', 'user_id']]
        ordering = ['-confirmed_at']
        verbose_name = '읽음 확인'
        verbose_name_plural = '읽음 확인 목록'

    def __str__(self):
        return f"{self.user_name} - {self.announcement.title}"


class BlockKitTemplate(models.Model):
    """Model for storing Slack Block Kit templates."""

    TEMPLATE_TYPES = [
        ('announcement', '공지 메시지'),
        ('home', '홈 화면'),
        ('modal', '모달'),
        ('reminder', '리마인더'),
    ]

    name = models.CharField(max_length=100, unique=True, verbose_name='템플릿 이름')
    template_type = models.CharField(
        max_length=20,
        choices=TEMPLATE_TYPES,
        verbose_name='템플릿 유형'
    )
    description = models.TextField(blank=True, verbose_name='설명')
    blocks = models.JSONField(verbose_name='Block Kit JSON')
    is_active = models.BooleanField(default=True, verbose_name='활성화')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')

    class Meta:
        ordering = ['template_type', 'name']
        verbose_name = 'Block Kit 템플릿'
        verbose_name_plural = 'Block Kit 템플릿 목록'

    def __str__(self):
        return f"{self.get_template_type_display()} - {self.name}"
