# discord_bot.py - Discord bot for alerts and queries
# Requirements: pip install discord.py requests

import discord
from discord.ext import commands, tasks
import requests
import os

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
ALERT_WEBHOOK = os.getenv('DISCORD_ALERT_WEBHOOK')

bot = commands.Bot(command_prefix='/')

@bot.event
async def on_ready():
    print(f'Bot ready: {bot.user}')
    check_alerts.start()

@tasks.loop(minutes=5)
async def check_alerts():
    # Fetch alerts from API
    resp = requests.get('https://findtorontoevents.ca/live-monitor/api/goldmine_tracker.php?action=alerts')
    data = resp.json()
    if data.get('ok') and data['active_count'] > 0:
        channel = bot.get_channel(123456789)  # Replace with channel ID
        for alert in data['alerts']:
            await channel.send(f"ALERT: {alert['title']} ({alert['severity']})")

@bot.command()
async def query(ctx, *, question):
    # Forward to your AI endpoint
    resp = requests.post('https://your-ai-endpoint', json={'query': question})
    answer = resp.json().get('answer', 'No response')
    await ctx.send(answer)

bot.run(DISCORD_TOKEN)