from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from ordered_model.models import OrderedModel
from django.utils.crypto import get_random_string
from django.urls import reverse
from django.contrib.sites.models import Site
from django.utils import timezone
from django.utils.text import slugify
import datetime


class User(AbstractUser):
    discord_id = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return '%s %s (%s)' % (self.first_name, self.last_name, self.discord_id)


class Server(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(null=True, blank=True, unique=True)
    discord_guild_id = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)

        super(Server, self).save(*args, **kwargs)


    def __str__(self):
        return self.name


class Channel(models.Model):
    name = models.CharField(max_length=255)
    server = models.ForeignKey('Server', on_delete=models.CASCADE, related_name='channels')
    slug = models.SlugField(null=True, blank=True)
    discord_channel_id = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)

        super(Channel, self).save(*args, **kwargs)
    
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
    private = models.BooleanField(default=False, help_text='If enabled only participants of the standup can view the standup, the public URL will be disabled!')

    def in_timeslot(self):
        now = timezone.localtime()
        if self.create_new_event_at.hour != now.hour:
            return False

        wd = now.weekday()

        if wd == 0:
            if self.create_on_monday:
                return True
        elif wd == 1:
            if self.create_on_tuesday:
                return True
        elif wd == 2:
            if self.create_on_wednesday:
                return True
        elif wd == 3:
            if self.create_on_thursday:
                return True
        elif wd == 4:
            if self.create_on_friday:
                return True
        elif wd == 5:
            if self.create_on_saturday:
                return True
        else:
            if self.create_on_sunday:
                return True

        return False


    def __str__(self):
        return self.name


class StandupQuestion(OrderedModel):
    standup_type = models.ForeignKey('StandupType', on_delete=models.CASCADE, related_name='questions')
    important = models.BooleanField(default=False, help_text='Will mark this answer as extra obvious if it is filled in')
    prefill_last_answer = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        related_name='to_prefill', 
        null=True, 
        blank=True)
    question = models.TextField()

    order_with_respect_to = 'standup_type'
    
    def __str__(self):
        return '%s -> %s' % (self.standup_type, self.question)


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
    
    def add_participant_from_discord(self, standup_type, discord_channel, discord_user, creating_discord_user):
        '''
        Add a Discord user to a Standup, creates the user if needed.
        '''
        user, _ = User.objects.get_or_create(discord_id=discord_user.id, defaults={'username': discord_user.id, 'first_name': discord_user.display_name, 'last_name': discord_user.discriminator})
        creating_user, _ = User.objects.get_or_create(discord_id=creating_discord_user.id, defaults={'username': creating_discord_user.id, 'first_name': creating_discord_user.display_name, 'last_name': creating_discord_user.discriminator})
        server, _ = Server.objects.get_or_create(discord_guild_id=discord_channel.guild.id, defaults={'name': discord_channel.guild.name})
        channel, _ = Channel.objects.get_or_create(discord_channel_id=discord_channel.id, server=server, defaults={'name': discord_channel.name})
        
        qs = StandupEvent.objects.filter(channel=channel, standup_type=standup_type)

        if not qs.exists():
            return (False, 'No standup available for this channel with this name')

        event = qs.first()

        att, created = event.attending.get_or_create(user=user, defaults={'created_by': creating_user})
        
        if created:
            return (True, None)
        else:
            return (False, 'Already in this standup!')



class StandupEvent(models.Model):
    channel = models.ForeignKey('Channel', on_delete=models.CASCADE, related_name='standups')
    standup_type = models.ForeignKey('StandupType', on_delete=models.PROTECT, related_name='standups')
    created_by = models.ForeignKey('User', on_delete=models.PROTECT, related_name='created_standups')
    created_at = models.DateTimeField(auto_now_add=True)

    objects = StandupEventManager()

    def initiate(self):
        '''
        Initialize a daily standup if there's no one yet and if the conditions for creating one are met.
        Returns True with the participant objects if it succeeded, False and None if there already was a event.
        '''
        today = timezone.localtime().date()
        att_users = []
        if not self.standup_type.in_timeslot():
            return (False, 'Not in timeslot')

        if not self.standups.filter(created_at__date=today).exists():
            s = Standup(event=self)
            s.save()

            for att in self.attending.filter(active=True):
                p = StandupParticipation(standup=s, user=att.user)
                p.save()
                att_users.append(p)

            return (True, att_users)

        return (False, 'A standup for today already exists')


    def __str__(self):
        return '%s -> %s' % (self.channel, self.standup_type)


class Attendee(models.Model):
    standup = models.ForeignKey('StandupEvent', on_delete=models.PROTECT, related_name='attending')
    user = models.ForeignKey('User', on_delete=models.PROTECT, related_name='attending')
    active = models.BooleanField(default=True)
    created_by = models.ForeignKey('User', on_delete=models.PROTECT, related_name='created_attendees')
    created_at = models.DateTimeField(auto_now_add=True)


class Standup(models.Model):
    event = models.ForeignKey('StandupEvent', on_delete=models.PROTECT, related_name='standups')
    created_at = models.DateTimeField(auto_now_add=True)
    pinned_message_id = models.CharField(max_length=255, null=True, blank=True)
    rebuild_message = models.BooleanField(default=False)
    
    def get_public_url(self):
        current_site = Site.objects.get_current().domain
        tz = timezone.get_default_timezone()
        cdate = self.created_at.astimezone(tz).date()

        return 'https://%s%s' % (current_site, reverse('public_standup', kwargs={
            'server': self.event.channel.server.slug, 
            'channel': self.event.channel.slug, 
            'standup_type': self.event.standup_type.command_name,
            'date': str(cdate)}))

    def __str__(self):
        return '%s -> %s' % (self.event, self.created_at.date())


class StandupParticipationManager(models.Manager):
    
    def active(self):
        return self.filter(completed=True).order_by('user__first_name')

    def inactive(self):
        return self.filter(completed=False).order_by('user__first_name')


class StandupParticipation(models.Model):
    standup = models.ForeignKey('Standup', on_delete=models.PROTECT, related_name='participants')
    user = models.ForeignKey('User', on_delete=models.PROTECT, related_name='participations')
    single_use_token = models.CharField(max_length=255, blank=True, null=True)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = StandupParticipationManager()

    def get_form_url(self):
        current_site = Site.objects.get_current().domain
        return 'https://%s%s' % (current_site, reverse('standup_form', kwargs={'token': self.single_use_token}))

    def get_private_url(self):
        current_site = Site.objects.get_current().domain
        return 'https://%s%s' % (current_site, reverse('private_standup', kwargs={'token': self.single_use_token}))

    def save(self, *args, **kwargs):
        if not self.single_use_token:
            self.single_use_token = get_random_string(length=48)

        if self.completed:
            su = self.standup
            su.rebuild_message = True
            su.save()

        super(StandupParticipation, self).save(*args, **kwargs)
    
    def __str__(self):
        return '%s -> %s#%s' % (self.standup, self.user.first_name, self.user.last_name)
    

class StandupParticipationAnswer(models.Model):
    participation = models.ForeignKey('StandupParticipation', on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey('StandupQuestion', on_delete=models.PROTECT, related_name='answers')
    answer = models.TextField(blank=True)

    class Meta:
        unique_together = (('participation', 'question'),)

