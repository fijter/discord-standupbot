from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.utils import timezone
from ordered_model.models import OrderedModel
from django.utils.crypto import get_random_string
from django.urls import reverse
from django.contrib.sites.models import Site
from django.utils import timezone
from timezone_field import TimeZoneField
from django.utils.text import slugify
import datetime


class User(AbstractUser):
    discord_id = models.CharField(max_length=255, null=True, blank=True)
    timezone = TimeZoneField(default=settings.TIME_ZONE)
    mute_until = models.DateField(null=True, blank=True)

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
    minimum_days_between_standups = models.IntegerField(default=0)
    private = models.BooleanField(default=False, help_text='If enabled only participants of the standup can view the standup, the public URL will be disabled!')
    public_publish_after = models.DurationField(default=datetime.timedelta(hours=24))
    publish_to_channel = models.BooleanField(default=False, help_text="publish to the channel even if it's a private standup")


    def in_timeslot(self, localtime):
        if not localtime:
            localtime = timezone.localtime()

        wd = localtime.weekday()

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
    
    def add_participant_from_discord(self, standup_type, discord_channel, discord_user, creating_discord_user, read_only=False):
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

        att, created = event.attending.get_or_create(user=user, defaults={'created_by': creating_user, 'read_only': read_only})
        
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

        att_users = []

        for att in self.attending.filter(active=True):
            aware_dt = timezone.localtime(timezone=att.user.timezone)
            s = self.standups.filter(standup_date=aware_dt.date()).first()

            # Don't create a participant if it's not a standup day
            if not self.standup_type.in_timeslot(aware_dt):
                continue
            
            # Don't create a standup if the minimum days have not passed yet
            if not s and self.standup_type.minimum_days_between_standups > 0:
                treshold = aware_dt - datetime.timedelta(days=self.standup_type.minimum_days_between_standups)
                if self.standups.filter(standup_date__gte=treshold.date()).exists():
                    continue


            # Don't create a participant if muted
            if att.user.mute_until and att.user.mute_until >= aware_dt.date():
                continue
            
            if not s:
                s = Standup(event=self, standup_date=aware_dt.date())
                s.save()
            
            # Skip users that are already created / received a notification
            if not s or StandupParticipation.objects.filter(standup=s, user=att.user, notified=True).exists():
                continue

            p, created = StandupParticipation.objects.get_or_create(standup=s, user=att.user, defaults={'read_only': att.read_only})

            if aware_dt.time() > self.standup_type.create_new_event_at and not p.notified:
                att_users.append(p)
                p.notified = True
                p.save()

        return (True, att_users)


    def __str__(self):
        return '%s -> %s' % (self.channel, self.standup_type)


class Attendee(models.Model):
    standup = models.ForeignKey('StandupEvent', on_delete=models.PROTECT, related_name='attending')
    user = models.ForeignKey('User', on_delete=models.PROTECT, related_name='attending')
    active = models.BooleanField(default=True)
    read_only = models.BooleanField(default=False)
    created_by = models.ForeignKey('User', on_delete=models.PROTECT, related_name='created_attendees')
    created_at = models.DateTimeField(auto_now_add=True)


class Standup(models.Model):
    event = models.ForeignKey('StandupEvent', on_delete=models.PROTECT, related_name='standups')
    standup_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    pinned_message_id = models.CharField(max_length=255, null=True, blank=True)
    rebuild_message = models.BooleanField(default=False)

    async def send_summary(self, bot):
        standup = self
        tz = timezone.get_default_timezone()
        # Check for the public notification release date
        startdate = timezone.datetime(
            standup.standup_date.year, 
            standup.standup_date.month, 
            standup.standup_date.day, 
            standup.event.standup_type.create_new_event_at.hour, 
            standup.event.standup_type.create_new_event_at.minute, 
            tzinfo=tz)

        notify_date = startdate + standup.event.standup_type.public_publish_after
        
        if timezone.now() < notify_date and standup.participants.inactive().exists():
            return

        msg = '** %s **\n** %s **\n' % (standup.event.standup_type.name, standup.standup_date.strftime('%A %b %d, %Y'))
        if not standup.event.standup_type.private:
            msg = '%s\n%s' % (msg, standup.get_public_url())

        channel_id = int(standup.event.channel.discord_channel_id)
        channel = bot.get_channel(channel_id)

        participants = standup.participants.active()
        
        # Don't send if the standup had no participant
        if not participants.exists():
            return

        msg_obj = await channel.send(msg)

        for parti in participants:
            if not parti.answers.exists():
                continue

            content = []
            for ans in parti.answers.all().order_by('question__order'):
                if not ans.answer:
                    continue
                    
                content.append('# %s\n%s' % (ans.question.question, ans.answer))

            content = '\n\n'.join(content)

            if len(content) > 1900:
                content = '%s...' % content[0:1900]

            msg = '<@%s>:\n```md\n%s```' % (parti.user.discord_id, content)
            
            await channel.send(msg)
        
        if standup.participants.inactive().exists():
            inactive = ', '.join(['<@%s>' % x.user.discord_id for x in standup.participants.inactive()])
            msg = 'Not filled in (yet) by: %s' % (inactive,)
            await channel.send(msg)

        await msg_obj.pin()
        standup.pinned_message_id = msg_obj.id
        standup.rebuild_message = False
        standup.save()

    def previous_standup(self):
        return Standup.objects.filter(id__lt=self.id, event=self.event).order_by('-id').first()
    
    def next_standup(self):
        return Standup.objects.filter(id__gt=self.id, event=self.event).order_by('id').first()
    
    def get_public_url(self):
        current_site = Site.objects.get_current().domain
        cdate = self.standup_date

        return 'https://%s%s' % (current_site, reverse('public_standup', kwargs={
            'server': self.event.channel.server.slug, 
            'channel': self.event.channel.slug, 
            'standup_type': self.event.standup_type.command_name,
            'date': str(cdate)}))

    def __str__(self):
        return '%s -> %s' % (self.event, self.standup_date)


class StandupParticipationManager(models.Manager):
    
    def active(self):
        return self.filter(completed=True, read_only=False).order_by('user__first_name')

    def inactive(self):
        return self.filter(completed=False, read_only=False).order_by('user__first_name')


class StandupParticipation(models.Model):
    standup = models.ForeignKey('Standup', on_delete=models.PROTECT, related_name='participants')
    user = models.ForeignKey('User', on_delete=models.PROTECT, related_name='participations')
    read_only = models.BooleanField(default=False)
    single_use_token = models.CharField(max_length=255, blank=True, null=True)
    completed = models.BooleanField(default=False)
    notified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = StandupParticipationManager()

    def previous_participation(self):
        return StandupParticipation.objects.filter(id__lt=self.id, standup__event=self.standup.event, user=self.user).order_by('-id').first()
    
    def next_participation(self):
        return StandupParticipation.objects.filter(id__gt=self.id, standup__event=self.standup.event, user=self.user).order_by('id').first()

    def get_form_url(self):
        current_site = Site.objects.get_current().domain
        return 'https://%s%s' % (current_site, reverse('standup_form', kwargs={'token': self.single_use_token}))

    def get_private_url(self):
        current_site = Site.objects.get_current().domain
        return 'https://%s%s' % (current_site, reverse('private_standup', kwargs={'token': self.single_use_token}))
    
    def get_home_url(self):
        current_site = Site.objects.get_current().domain
        return 'https://%s%s' % (current_site, reverse('private_home', kwargs={'token': self.single_use_token}))

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

