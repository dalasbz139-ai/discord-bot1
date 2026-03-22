import discord
import os
import asyncio
from dotenv import load_dotenv
import sys

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.guild_messages = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    for guild in client.guilds:
        print(f"Guild: {guild.name} (ID: {guild.id})")
        print("Roles:")
        for role in guild.roles:
            print(f"- {role.name} (ID: {role.id})")
        print("Categories/Channels:")
        # First channels without category
        for channel in guild.channels:
            if channel.category is None:
                print(f"Channel (no category): {channel.name} ({type(channel).__name__})")
        
        for category in guild.categories:
            print(f"Category: {category.name}")
            for channel in category.channels:
                print(f"  - {channel.name} ({type(channel).__name__})")
    await client.close()

if __name__ == "__main__":
    client.run(TOKEN)
