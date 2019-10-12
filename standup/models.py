from django.db import models
from django.contrib.auth.models import AbstractUser
from ordered_model.models import OrderedModel
import datetime


class User(AbstractUser):
    discord_id = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return '%s %s (%s)' % (self.first_name, self.last_name, self.discord_id)


class Server(models.Model):
    name = models.CharField(max_length=255)
    discord_guild_id = models.IntegerField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Channel(models.Model):
    name = models.CharField(max_length=255)
    server = models.ForeignKey('Server', on_delete=models.CASCADE, related_name='channels')
    discord_channel_id = models.IntegerField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return '%s -> #%s' % (self.server.name, self.name)


class StandupType(models.Model):
    name = models.CharField(max_length=100)
    command_name = models.SlugField(unique=True)
    create_new_event_at = models.TimeField(default=datetime.time(0))
    create_on_monday = models.BooleanField(default=True)
    create_on_tuesday = models.BooleanField(default=True)
    create_on_wednesday = models.BooleanField(default=True)
    create_on_thursday = models.BooleanField(default=True)
    create_on_friday = models.BooleanField(default=True)
    create_on_saturday = models.BooleanField(default=False)
    create_on_sunday = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class StandupQuestion(OrderedModel):
    standup_type = models.ForeignKey('StandupType', on_delete=models.CASCADE, related_name='questions')
    question = models.TextField()

    order_with_respect_to = 'standup_type'
    
    def __str__(self):
        return self.question


class StandupEventManager(models.Manager):
    
    def create_from_discord(self, standup_type, discord_channel, discord_user):
        '''
        Turns some raw Discord ID's into the right objects, or fetches them if 
        they already exists and creates the corrosponding Standup Event 
        if it's not there yet.
        '''
        user, _ = User.objects.get_or_create(discord_id=discord_user.id, defaults={'username': discord_user.id, 'first_name': discord_user.display_name, 'last_name': discord_user.discriminator})
        server, _ = Server.objects.get_or_create(discord_guild_id=discord_channel.guild.id, defaults={'name': discord_channel.guild.name})
        channel, _ = Channel.objects.get_or_create(discord_channel_id=discord_channel.id, server=server, defaults={'name': discord_channel.name})
        
        if StandupEvent.objects.filter(channel=channel, standup_type=standup_type).exists():
            return False

        StandupEvent(channel=channel, standup_type=standup_type, created_by=user).save()
        return True


class StandupEvent(models.Model):
    channel = models.ForeignKey('Channel', on_delete=models.CASCADE, related_name='standups')
    standup_type = models.ForeignKey('StandupType', on_delete=models.PROTECT, related_name='standups')
    created_by = models.ForeignKey('User', on_delete=models.PROTECT, related_name='created_standups')
    created_at = models.DateTimeField(auto_now_add=True)

    objects = StandupEventManager()

    def __str__(self):
        return '%s -> %s' % (self.channel, self.standup_type)


class Attendee(models.Model):
    standup = models.ForeignKey('StandupEvent', on_delete=models.PROTECT, related_name='attending')
    user = models.ForeignKey('User', on_delete=models.PROTECT, related_name='attending')
    created_by = models.ForeignKey('User', on_delete=models.PROTECT, related_name='created_attendees')
    created_at = models.DateTimeField(auto_now_add=True)


class Standup(models.Model):
    event = models.ForeignKey('StandupEvent', on_delete=models.PROTECT, related_name='dailies')
    created_at = models.DateTimeField(auto_now_add=True)
    pinned_message_id = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return '%s -> %s' % (self.event, self.created_at.date())


class StandupParticipation(models.Model):
    standup = models.ForeignKey('Standup', on_delete=models.PROTECT, related_name='participants')
    user = models.ForeignKey('User', on_delete=models.PROTECT, related_name='participations')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return '%s -> %s#%s' % (self.standup, self.user.first_name, self.user.last_name)
    

class StandupParticipationAnswer(models.Model):
    participation = models.ForeignKey('StandupParticipation', on_delete=models.PROTECT, related_name='answers')
    question = models.ForeignKey('StandupQuestion', on_delete=models.PROTECT, related_name='answers')
    answer = models.TextField(blank=True)

    class Meta:
        unique_together = (('participation', 'question'),)
