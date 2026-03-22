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

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    guild = client.guilds[0]
    
    # Target Category
    category_name = "🛡️ DISCORD LOGS"
    category = discord.utils.get(guild.categories, name=category_name)
    
    if not category:
        print(f"Category {category_name} not found!")
        await client.close()
        return

    # Find channels to move
    channels_to_move = [ch for ch in guild.text_channels if ch.name.startswith("closedorder-") and ch.category != category]
    
    print(f"Found {len(channels_to_move)} tickets to move.")
    
    moved_count = 0
    for i, ch in enumerate(channels_to_move):
        try:
            # Move to category
            # Note: A category can only have 50 channels. 
            # If we have more, we might need multiple categories.
            # But let's see how many we have.
            
            if len(category.channels) >= 50:
                # Create a new log category if full
                new_cat_name = f"{category_name} { (len(guild.categories) - 5) // 1 + 1 }" # Rough numbering
                # Actually, simpler logic:
                category = await guild.create_category(f"🛡️ LOGS {moved_count // 45 + 1}")
                print(f"Created new category for overflow: {category.name}")

            await ch.edit(category=category)
            moved_count += 1
            print(f"[{i+1}/{len(channels_to_move)}] Moved {ch.name} to {category.name}")
            
            # Avoid rate limits
            if (i + 1) % 5 == 0:
                await asyncio.sleep(2) # Small pause
                
        except Exception as e:
            print(f"Error moving {ch.name}: {e}")
            await asyncio.sleep(5) # Longer pause if error

    print(f"Finished moving {moved_count} tickets.")
    await client.close()

if __name__ == "__main__":
    client.run(TOKEN)
