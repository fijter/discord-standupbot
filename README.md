# Discord Daily standup bot

This generic bot will allow you to enable asynchronous daily standups in Discord.
By initializing the bot in a channel participants will be able to enter their
daily tasks in a web form which will be bundled and posted in the channel in a
pinned message. 

## Current status

[x] Boilerplate bot code
[x] Basic models
[x] Creating new Daily Standup Channels
[ ] Creating the Admin interface
[ ] Creating the web form on single use URLs 
[ ] Allowing people to subscribe to the daily of a channel
[ ] Allowing people to submit their report
[ ] Sending daily reminders
[ ] Updating and pinning the aggregated daily
[ ] Clean up and testing
[ ] Implementing a nice design


## How to add the bot to your Discord server

- Create a Discord bot token on https://discordapp.com/developers
- Create a .env file and enter your Discord token: `DISCORD_TOKEN=TOKENHERE`
- Invite the bot to your server with this URL: https://discordapp.com/api/oauth2/authorize?permissions=67497024&scope=bot&client_id=YOUR_BOTS_DISCORD_CLIENT_ID
