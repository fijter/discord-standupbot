from django.contrib import admin
from ordered_model.admin import OrderedTabularInline, OrderedInlineModelAdminMixin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from . import models


class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'discord_id', 'mute_until', 'is_staff')
    fieldsets = BaseUserAdmin.fieldsets + (('Discord', {'fields': ('discord_id', 'timezone', 'mute_until')}),)


class StandupEventAdmin(admin.ModelAdmin):
    list_display = ('channel', 'standup_type', 'created_by', 'created_at')
    raw_id_fields = ('channel', 'created_by',)


class StandupQuestionInline(OrderedTabularInline):
    model = models.StandupQuestion
    fields = ('question', 'important', 'prefill_last_answer', 'order', 'move_up_down_links',)
    readonly_fields = ('order', 'move_up_down_links',)
    extra = 0
    ordering = ('order',)


class StandupTypeAdmin(OrderedInlineModelAdminMixin, admin.ModelAdmin):
    list_display = ('name', 'command_name')
    inlines = (StandupQuestionInline,)


class StandupParticipationAnswerInline(admin.TabularInline):
    model = models.StandupParticipationAnswer
    fields = ('question', 'answer')
    raw_id_fields = ('question',)
    extra = 0
    ordering = ('question__order',)


class StandupParticipationAdmin(admin.ModelAdmin):
    list_display = ('standup', 'user', 'created_at')
    raw_id_fields = ('standup', 'user')
    inlines = (StandupParticipationAnswerInline,)


class AttendeeAdmin(admin.ModelAdmin):
    list_display = ('standup', 'user', 'active', 'created_by', 'created_at',)
    raw_id_fields = ('standup', 'user',)


admin.site.register(models.User, UserAdmin)
admin.site.register(models.Server)
admin.site.register(models.Channel)
admin.site.register(models.StandupType, StandupTypeAdmin)
admin.site.register(models.StandupEvent, StandupEventAdmin)
admin.site.register(models.Standup)
admin.site.register(models.Attendee, AttendeeAdmin)
admin.site.register(models.StandupParticipation, StandupParticipationAdmin)
