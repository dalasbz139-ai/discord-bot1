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
intents.members = True
intents.guild_messages = True
intents.message_content = True

client = discord.Client(intents=intents)

async def setup_server(guild):
    print(f"Starting setup for Guild: {guild.name}")
    
    # 1. Define Categories and Channels
    structure = {
        "📚 INFO": ["welcome", "rules", "announcements"],
        "🛒 KARYS SHOP": ["prices", "vbucks", "nitro", "spotify", "boost", "gift", "payment-methods"],
        "🎟️ SUPPORT & ORDERS": ["ticket-panel"],
        "🗂️ TICKET LOGS": ["logs"],
        "🛡️ DISCORD LOGS": ["audit-log", "message-logs", "member-logs", "server-logs", "moderation-logs"] # Added DISCORD LOGS
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
        # Check if category exists
        category = discord.utils.get(guild.categories, name=cat_name)
        if not category:
            overwrites = overwrites_admin_only if "LOGS" in cat_name else None
            category = await guild.create_category(cat_name, overwrites=overwrites)
            print(f"Created Category: {cat_name}")
        
        for ch_name in channels:
            # Check if channel exists
            channel = discord.utils.get(category.text_channels, name=ch_name)
            if not channel:
                # Logs category is admin only
                overwrites = overwrites_admin_only if "LOGS" in cat_name else overwrites_public
                channel = await guild.create_text_channel(ch_name, category=category, overwrites=overwrites)
                print(f"Created Channel: {ch_name} in {cat_name}")
            else:
                print(f"Channel {ch_name} already exists in {cat_name}")

    print("Server setup complete!")

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    for guild in client.guilds:
        await setup_server(guild)
    print("All tasks finished. Closing bot.")
    await client.close()

if __name__ == "__main__":
    client.run(TOKEN)
