import discord
import asyncio
from django.core.management.base import BaseCommand, CommandError
from discord.ext.commands import Bot
from django.conf import settings
from standup import models


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

        @bot.command(name='newstandup')
        async def newstandup(ctx):
            if not ctx.author.permissions_in(ctx.channel).manage_roles:
                await ctx.author.send('Sorry, you have no permission to do this! Only users with the permission to manage roles for a given channel can do this.')
            else:
                if models.StandupEvent.objects.create_from_discord(ctx.channel, ctx.author):
                    await ctx.send('Daily startup initialized!')
                else:
                    await ctx.send('This channel already has a daily standup, no new one was created.')


            await ctx.message.delete()

	    
        async def interval():
            await asyncio.sleep(3)
    
            while True:
                # Repetitive task checks here
                await asyncio.sleep(3)

        try:
            bot.loop.run_until_complete(asyncio.gather(bot.start(settings.DISCORD_TOKEN), interval()))
        except KeyboardInterrupt:
            bot.loop.run_until_complete(bot.logout())
        finally:
            bot.loop.close()
