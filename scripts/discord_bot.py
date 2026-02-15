# discord_bot.py - Discord bot for alerts, queries, and event resources
# Requirements: pip install discord.py requests

import discord
from discord.ext import commands, tasks
from datetime import datetime
import requests
import os

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
ALERT_WEBHOOK = os.getenv('DISCORD_ALERT_WEBHOOK')
RESOURCES_API = 'https://findtorontoevents.ca/api/events/resources.php'

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
async def resources(ctx, category: str = None):
    """Browse 50+ Toronto event resources, optionally filtered by category.
    Categories: platforms, calendars, music, arts, theatre, sports, festivals, food, media
    """
    params = {'today': '1'}
    if category:
        params['category'] = category.lower()

    try:
        resp = requests.get(RESOURCES_API, params=params, timeout=10)
        data = resp.json()
    except Exception as e:
        await ctx.send(f"Could not load resources. Visit: <https://findtorontoevents.ca/resources/resources.html>")
        return

    if not data.get('ok'):
        await ctx.send("Error loading resources. Visit: <https://findtorontoevents.ca/resources/resources.html>")
        return

    msg = ""

    # Show today's events if any
    todays = data.get('todays_events', [])
    if todays:
        today_date = data.get('today_date', datetime.now().strftime('%A, %B %d, %Y'))
        msg += f"**Happening Today in Toronto**\n*{today_date}*\n\n"
        for evt in todays[:10]:
            emoji = evt.get('category_emoji', '')
            price = f" — {evt['price']}" if evt.get('price') and evt['price'] != 'Check Site' else ""
            msg += f"{emoji} **{evt['title']}**{price}\n"
            msg += f"   {evt['source']}"
            if evt.get('source_url'):
                msg += f" • [Visit]({evt['source_url']})"
            msg += "\n"
        if len(todays) > 10:
            msg += f"\n*...and {len(todays) - 10} more*\n"
        msg += "\n"

    # Show categories
    cats = data.get('categories', [])
    if category and cats:
        cat = cats[0]
        msg += f"{cat.get('emoji', '')} **{cat['name']}**\n\n"
        for src in cat.get('sources', []):
            badge = f" `{src['badge']}`" if src.get('badge') else ""
            msg += f"**{src['name']}**{badge}\n{src['description']}\n{src['url']}\n"
            for evt in src.get('events', []):
                price = f" ({evt['price']})" if evt.get('price') else ""
                msg += f"  • {evt['title']} — {evt['date']}{price}\n"
            msg += "\n"
    elif cats:
        msg += "**Toronto Event Resources — 50+ Sources**\n\n"
        for cat in cats:
            count = len(cat.get('sources', []))
            top = [f"[{s['name']}]({s['url']})" for s in cat.get('sources', [])[:3]]
            extra = f" + {count - 3} more" if count > 3 else ""
            msg += f"{cat.get('emoji', '')} **{cat['name']}** ({count} sources)\n"
            msg += f"   {' • '.join(top)}{extra}\n\n"
        msg += "Use `/resources <category>` for details!\n"
        msg += "Categories: `platforms` `calendars` `music` `arts` `theatre` `sports` `festivals` `food` `media`\n"

    msg += f"\nFull page: <https://findtorontoevents.ca/resources/resources.html>"

    # Discord has 2000 char limit
    if len(msg) > 1990:
        msg = msg[:1987] + "..."

    await ctx.send(msg)

@bot.command()
async def today(ctx):
    """Show events happening today from all Toronto event resources."""
    params = {'today': '1'}
    try:
        resp = requests.get(RESOURCES_API, params=params, timeout=10)
        data = resp.json()
    except Exception:
        await ctx.send("Could not load today's events. Visit: <https://findtorontoevents.ca/>")
        return

    todays = data.get('todays_events', [])
    if not todays:
        await ctx.send("No specific events found for today in our resource listings. Check <https://findtorontoevents.ca/> for live event data!")
        return

    today_date = data.get('today_date', datetime.now().strftime('%A, %B %d, %Y'))
    msg = f"**Happening Today in Toronto**\n*{today_date}*\n\n"
    for evt in todays[:15]:
        emoji = evt.get('category_emoji', '')
        price = f" — {evt['price']}" if evt.get('price') and evt['price'] != 'Check Site' else ""
        msg += f"{emoji} **{evt['title']}**{price}\n"
        msg += f"   {evt['source']}"
        if evt.get('source_url'):
            msg += f" • [Visit]({evt['source_url']})"
        msg += "\n"
    if len(todays) > 15:
        msg += f"\n*...and {len(todays) - 15} more*\n"
    msg += f"\nSee all: <https://findtorontoevents.ca/resources/resources.html>"

    if len(msg) > 1990:
        msg = msg[:1987] + "..."
    await ctx.send(msg)

@bot.command()
async def query(ctx, *, question):
    # Forward to your AI endpoint
    resp = requests.post('https://your-ai-endpoint', json={'query': question})
    answer = resp.json().get('answer', 'No response')
    await ctx.send(answer)

bot.run(DISCORD_TOKEN)