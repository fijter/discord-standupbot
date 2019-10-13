# Discord Daily standup bot

This generic bot will allow you to enable asynchronous daily standups in Discord.
By initializing the bot in a channel participants will be able to enter their
daily tasks in a web form which will be bundled and posted in the channel in a
pinned message. 

## Current status

- [x] Boilerplate bot code
- [x] Basic models
- [x] Creating new Daily Standup Channels
- [x] Creating the Admin interface
- [x] Allowing people to subscribe to the daily of a channel
- [x] Support multiple standup types with different questions (configurable)
- [x] Creating the web form on single use URLs 
- [x] Allowing people to submit their report
- [x] Sending daily reminders
- [ ] Updating and pinning the aggregated daily
- [ ] Historical overview of standups on webpage
- [ ] Clean up and testing
- [ ] Implementing a nice design


## How to add the bot to your Discord server

- Create a Discord bot token on https://discordapp.com/developers
- Create a .env file and enter your Discord token: `DISCORD_TOKEN=TOKENHERE`
- Invite the bot to your server with this URL: https://discordapp.com/api/oauth2/authorize?permissions=67497024&scope=bot&client_id=YOUR_BOTS_DISCORD_CLIENT_ID


## Installation

 - Create a `.env` file with `DISCORD_TOKEN=TOKENHERE` in it
 - Tweak any settings in `standup/settings.py` to your needs
 - Run the Django server (`python manage.py runserver` for a dev server, production deploy with gunicorn or uwsgi on demand)
 - Run the `python manage.py run_bot` command in a seperate background process (supervisord)
 - Run `python manage.py createsuperuser` to create a admin user
 - Go to the admin on `/admin` in your browser, log in and....
   - Update the Site in Sites to match your servers URL
   - Set up the first standup types with questions
 - Start using the bot in Discord using the `!newstandup` and `!addparticipant` commands
