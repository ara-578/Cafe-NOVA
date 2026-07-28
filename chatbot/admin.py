from django.contrib import admin
from .models import ChatSession, ChatMessage, MenuItem, ContactMessage


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ("role", "content", "created_at")


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ("session_id", "created_at")
    inlines = [ChatMessageInline]


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "is_special", "is_available")
    list_filter = ("category", "is_special", "is_available")
    search_fields = ("name", "description")


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "subject", "created_at")
    readonly_fields = ("name", "email", "phone", "subject", "message", "created_at")
