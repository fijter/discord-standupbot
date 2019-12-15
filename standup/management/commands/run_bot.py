import discord
import asyncio
from django.core.management.base import BaseCommand, CommandError
from discord.ext.commands import Bot, MemberConverter, errors
import discord
from django.conf import settings
from django.utils import timezone
import datetime
from standup import models
import pytz


class Command(BaseCommand):
    help = 'Runs the Discord Bot'

    def handle(self, *args, **options):
        bot = Bot(command_prefix='!')

        print('-----------------------------------')
        print('Starting the bot...')

        @bot.event
        async def on_ready():
            print('-----------------------------------')
            print('Bot logged in as %s (%s)' % (bot.user.name, bot.user.id))
            print('-----------------------------------')
        
        bot.remove_command('help')

        @bot.command()
        async def standup(ctx):
            try:
                await ctx.message.delete()
            except discord.errors.Forbidden:
                pass

            embed = discord.Embed(title="**StandupBot Help**", description="These commands are available:")
            embed.add_field(name="**!timezones**", value="Shows all available timezones to pick from", inline=False)
            embed.add_field(name="**!findtimezone <name>**", value="Shows all available timezones to pick from matching the given name, for easier lookup", inline=False)
            embed.add_field(name="**!settimezone <tz_name>**", value="Set a timezone from the `!timezones` list", inline=False)
            embed.add_field(name="**!mute_until <yyyy/mm/dd>**", value="Mute yourself from standup participation until a given date, good for vacations", inline=False)
            embed.add_field(name="**!newstandup <standup_type>**", value="Start a new standup for the channel you are in", inline=False)
            embed.add_field(name="**!addparticipant <standup_type> [readonly] <user 1> <user 2>...**", value="Add a new participant for a standup, optionally read only. You can add multiple add the same time", inline=False)
            
            await ctx.author.send(embed=embed)
        
        @bot.command(name='sendsummary')
        async def sendsummary(ctx, standup_type):

            await ctx.message.delete()

            if not ctx.author.permissions_in(ctx.channel).manage_messages:
                await ctx.author.send('Sorry, you have no permission to do this! Only users with the permission to manage messages for a given channel can do this.')
                return

            try:
                stype = models.StandupType.objects.get(command_name=standup_type)
            except models.StandupType.DoesNotExist:
                msg = 'Please provide a valid standup type as the argument of this function, your options are:\n\n'
                msg += '\n'.join(['`%s` (%s)' % (s.command_name, s.name) for s in models.StandupType.objects.all()])
                await ctx.author.send(msg)
                return 
            
            today = timezone.now().date()

            standup = models.Standup.objects.filter(event__standup_type=stype, event__channel__discord_channel_id=ctx.channel.id, event__standup_type__publish_to_channel=True, standup_date__lt=today).order_by('-id').first()

            if standup:
                await ctx.author.send('Sending summary for %s' % standup)
                await standup.send_summary(bot)
            else:
                await ctx.author.send('Standup not found, can\'t publish!')

        @bot.command(name='addparticipant')
        async def addparticipant(ctx, standup_type, *users):

            await ctx.message.delete()

            users = list(users)
            read_only = False

            if users[0] == 'readonly':
                users.pop(0)
                read_only = True
            
            if not ctx.author.permissions_in(ctx.channel).manage_messages:
                await ctx.author.send('Sorry, you have no permission to do this! Only users with the permission to manage roles for a given channel can do this.')
                return

            try:
                stype = models.StandupType.objects.get(command_name=standup_type)
            except models.StandupType.DoesNotExist:
                msg = 'Please provide a valid standup type as the argument of this function, your options are:\n\n'
                msg += '\n'.join(['`%s` (%s)' % (s.command_name, s.name) for s in models.StandupType.objects.all()])
                await ctx.author.send(msg)
                return 

            members = []
            failed = []
            for user in users:
                try:
                    mem = await MemberConverter().convert(ctx, user)
                except errors.BadArgument:
                    continue

                success, reason = models.StandupEvent.objects.add_participant_from_discord(stype, ctx.channel, mem, ctx.author, read_only)

                if success:
                    members.append(mem)

                if not success:
                    failed.append((mem, reason))


                print(success, reason)
            
            if members:
                mstring = ', '.join(['<@%s>' % x.id for x in members])
                await ctx.send('Added %s as participants of this standup!' % mstring)

            if failed:
                for mem, reason in failed:
                    await ctx.send('Failed to add <@%s> as participants of this standup, %s.' % (mem.id, reason))



        @bot.command(name='timezones')
        async def timezones(ctx):

            try:
                await ctx.message.delete()
            except discord.errors.Forbidden:
                pass

            await ctx.author.send('**You can choose from the following timezones:**')
            
            # looping over slices of all timezones, working around max. message length of Discord
            for i in range((len(pytz.common_timezones) // 75) + 1):
                tzs = pytz.common_timezones[i*75:i*75+75]
                msg = '`%s`' % '`, `'.join(tzs)
                await ctx.author.send(msg)
        

        @bot.command(name='findtimezone')
        async def findtimezone(ctx, name):
            try:
                await ctx.message.delete()
            except discord.errors.Forbidden:
                pass

            await ctx.author.send('**Found the following timezones for `%s`:**' % name)
            
            # looping over slices of all timezones, working around max. message length of Discord
            ftzs = [x for x in pytz.common_timezones if name.lower() in x.lower()]
            for i in range((len(ftzs) // 75) + 1):
                tzs = ftzs[i*75:i*75+75]
                msg = '`%s`' % '`, `'.join(tzs)
                await ctx.author.send(msg)
        

        @bot.command(name='settimezone')
        async def settimezone(ctx, timezonename):
            try:
                await ctx.message.delete()
            except discord.errors.Forbidden:
                pass

            if timezonename in pytz.common_timezones:
                user, _ = models.User.objects.get_or_create(
                    discord_id=ctx.author.id, 
                    defaults={
                        'username': ctx.author.id, 
                        'first_name': ctx.author.display_name, 
                        'last_name': ctx.author.discriminator
                    })

                user.timezone = timezonename
                user.save()

                await ctx.author.send('Thanks, your timezone has been set to %s' % user.timezone)
            else:
                await ctx.author.send('%s is a unknown timezone, please execute the `!timezones` command to see all avaiable timezones!' % timezonename)

        @bot.command(name='mute_until')
        async def mute_until(ctx, date):
            try:
                await ctx.message.delete()
            except discord.errors.Forbidden:
                pass
        
            try:
                until = datetime.date(*[int(x) for x in date.split('/')])
            except:
                await ctx.author.send('Unable to mute you, date format unknown. Please provide a date like this: YYYY/MM/DD, so for example `!mute_until 2020/01/01`')
                
            user, _ = models.User.objects.get_or_create(
                discord_id=ctx.author.id, 
                defaults={
                    'username': ctx.author.id, 
                    'first_name': ctx.author.display_name, 
                    'last_name': ctx.author.discriminator
                })
            
            user.mute_until = until
            user.save()

            await ctx.author.send('Thanks, you won\'t participate in standups until %s' % until)


        @bot.command(name='newstandup')
        async def newstandup(ctx, standup_type):
            
            try:
                stype = models.StandupType.objects.get(command_name=standup_type)
            except models.StandupType.DoesNotExist:
                msg = 'Please provide a valid standup type as the argument of this function, your options are:\n\n'
                msg += '\n'.join(['`%s` (%s)' % (s.command_name, s.name) for s in models.StandupType.objects.all()])
                await ctx.author.send(msg)
                await ctx.message.delete()
                return 

            if not ctx.author.permissions_in(ctx.channel).manage_messages:
                await ctx.author.send('Sorry, you have no permission to do this! Only users with the permission to manage roles for a given channel can do this.')
            else:
                if models.StandupEvent.objects.create_from_discord(stype, ctx.channel, ctx.author):
                    await ctx.send('%s initialized for this channel!' % stype.name)
                else:
                    await ctx.send('This channel already has a %s, no new one was created.' % stype.name)


            await ctx.message.delete()

	    
        async def interval():
            await asyncio.sleep(10)

            tz = timezone.get_default_timezone()
    
            while True:
                # Repetitive task checks here
                for ev in models.StandupEvent.objects.all():
                    success, to_notify = ev.initiate()
                    if success:
                        for participant in to_notify:
                            did = int(participant.user.discord_id)
                            user = bot.get_user(did)
                            try:

                                if not participant.read_only:
                                    await user.send('Please answer the questions for "%s" in "%s" here: %s - Thanks!' % (
                                        participant.standup.event.standup_type.name, 
                                        participant.standup.event.channel, 
                                        participant.get_form_url(),))

                                await user.send('You can view your private standup overview here: %s' % (
                                participant.get_home_url(),))
                            except Exception as e:
                                print('Something went wrong while sending form to the user: %s' % e)

                for standup in models.Standup.objects.filter(pinned_message_id__isnull=True, rebuild_message=True, event__standup_type__publish_to_channel=True):
                    await standup.send_summary(bot)
                                

                await asyncio.sleep(10)

        try:
            bot.loop.run_until_complete(asyncio.gather(bot.start(settings.DISCORD_TOKEN), interval()))
        except KeyboardInterrupt:
            bot.loop.run_until_complete(bot.logout())
        finally:
            bot.loop.close()
