import discord
import os
import asyncio
from dotenv import load_dotenv
import sys

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

intents = discord.Intents.default()
intents.guilds = True

client = discord.Client(intents=intents)

async def setup_server(guild):
    print(f"Starting pretty setup for Guild: {guild.name}")
    
    # 1. Define Categories and Pretty Channels
    # Format: "Emoji Name"
    structure = {
        "〢─ INFO ─〢": {
            "welcome": "💬・welcome",
            "rules": "📜・rules",
            "announcements": "📢・announcements"
        },
        "🛒〢─ KARYS SHOP ─〢": {
            "prices": "💰・valorant-points",
            "vbucks": "🎮・v-bucks",
            "nitro": "🚀・discord-nitro",
            "spotify": "🎵・spotify-premium",
            "boost": "💎・server-boosts",
            "gift": "🎁・valorant-gifting",
            "payment-methods": "💳・payment-methods"
        },
        "🎟️〢─ SUPPORT ─〢": {
            "ticket-panel": "📩・open-ticket"
        },
        "🛡️〢─ LOGS ─〢": {
            "logs": "📑・ticket-logs",
            "audit-log": "🛡️・audit-log",
            "message-logs": "💬・message-logs",
            "member-logs": "👥・member-logs",
            "server-logs": "💻・server-logs",
            "moderation-logs": "⚖️・moderation-logs"
        }
    }
    
    overwrites_public = {
        guild.default_role: discord.PermissionOverwrite(send_messages=False, read_messages=True),
        guild.me: discord.PermissionOverwrite(send_messages=True, read_messages=True, administrator=True)
    }
    
    overwrites_admin_only = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True, administrator=True)
    }

    for cat_name, channels in structure.items():
        # Check if category exists (finding it by the base name to avoid duplicates if I rename)
        base_cat_name = cat_name.split("─")[1].strip() if "─" in cat_name else cat_name
        category = None
        for c in guild.categories:
            if base_cat_name in c.name:
                category = c
                break
        
        if not category:
            category = await guild.create_category(cat_name)
            print(f"Created Category: {cat_name}")
        else:
            await category.edit(name=cat_name)
            print(f"Renamed Category to: {cat_name}")
        
        for old_slug, pretty_name in channels.items():
            # Try to find channel by slug or by the new pretty name
            channel = None
            for ch in category.text_channels:
                if old_slug in ch.name or pretty_name in ch.name:
                    channel = ch
                    break
            
            if not channel:
                overwrites = overwrites_admin_only if "LOGS" in cat_name else overwrites_public
                channel = await guild.create_text_channel(pretty_name, category=category, overwrites=overwrites)
                print(f"Created Channel: {pretty_name}")
            else:
                await channel.edit(name=pretty_name)
                print(f"Renamed Channel to: {pretty_name}")

    print("Pretty setup complete!")

@client.event
async def on_ready():
    for guild in client.guilds:
        await setup_server(guild)
    await client.close()

if __name__ == "__main__":
    client.run(TOKEN)
