from django.db import models
from django.contrib.auth.models import AbstractUser
import datetime


class User(AbstractUser):
    discord_id = models.IntegerField(null=True, blank=True)


class Server(models.Model):
    name = models.CharField(max_length=255)
    discord_guild_id = models.IntegerField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Channel(models.Model):
    name = models.CharField(max_length=255)
    server = models.ForeignKey('Server', on_delete=models.CASCADE, related_name='channels')
    discord_channel_id = models.IntegerField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)


class StandupEventManager(models.Manager):
    
    def create_from_discord(self, discord_channel, discord_user):
        '''
        Turns some raw Discord ID's into the right objects, or fetches them if 
        they already exists and creates the corrosponding Standup Event 
        if it's not there yet.
        '''
        user, _ = User.objects.get_or_create(discord_id=discord_user.id, defaults={'username': discord_user.id, 'first_name': discord_user.display_name, 'last_name': discord_user.discriminator})
        server, _ = Server.objects.get_or_create(discord_guild_id=discord_channel.guild.id, defaults={'name': discord_channel.guild.name})
        channel, _ = Channel.objects.get_or_create(discord_channel_id=discord_channel.id, server=server, defaults={'name': discord_channel.name})
        
        if StandupEvent.objects.filter(channel=channel).exists():
            return False

        StandupEvent(channel=channel, created_by=user).save()
        return True


class StandupEvent(models.Model):
    channel = models.ForeignKey('Channel', on_delete=models.CASCADE, related_name='standups')
    create_new_event_at = models.TimeField(default=datetime.time(0))
    created_by = models.ForeignKey('User', on_delete=models.PROTECT, related_name='created_standups')
    created_at = models.DateTimeField(auto_now_add=True)

    objects = StandupEventManager()


class DailyStandup(models.Model):
    standup = models.ForeignKey('StandupEvent', on_delete=models.PROTECT, related_name='dailies')
    created_at = models.DateTimeField(auto_now_add=True)
