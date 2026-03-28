import discord
import os
import asyncio
from dotenv import load_dotenv
from datetime import datetime
import random

load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# Common Moroccan/Global Usernames for realism
FAKE_USERS = [
    "ka_ii11", "simo_dz", "anass_vlr", "amine99", "reda_king", "youssef_7",
    "soufiane_x", "hamza_vp", "mehdi_pro", "ismail_01", "omar_vlr", "yassine_vp",
    "khalid88", "walid_shop", "mourad_vlr", "zakaria_7", "achraf_vp", "ayoub_94",
    "yassine_l7", "kamal_boss", "hicham_vlr", "nabil_vp", "othmane_7", "adam_pro"
]

# Service details
SERVICES = {
    "Valorant Orders": [
        "1,000 VP | 5.0 $ | 50 dh", 
        "5,000 VP | 25.0 $ | 250 dh", 
        "10,000 VP | 50.0 $ | 500 dh"
    ],
    "Gifting Orders": [
        "BLACKTHORN BUNDLE (8,700 VP) | 43.5 $ | 435.0 DH",
        "BLACKTHORN VANDAL (2,175 VP) | 10.88 $ | 108.75 DH",
        "VCT X NS (2,320 VP) | 11.6 $ | 116.0 DH",
        "LUNAR 26 (2,320 VP) | 11.6 $ | 116.0 DH"
    ],
    "Valorant Points": [
        "20,000 VP | 105.0 $ | 1050 dh", 
        "11,000 VP | 55.0 $ | 550 dh", 
        "15,000 VP | 75.0 $ | 750 dh"
    ]
}

PAYMENT_METHODS = ["CIH Bank", "Cash Plus", "Binance (USDT)", "BMCE Bank"]

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
client = discord.Client(intents=intents)

async def create_fake_ticket(guild, category, cat_name):
    try:
        if not FAKE_USERS: return
        user_name = random.choice(FAKE_USERS)
        FAKE_USERS.remove(user_name)
        
        prefix = "order-gifting" if "Gifting" in cat_name else "order-vp"
        channel_name = f"{prefix}-{user_name}"
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, administrator=True)
        }
        
        channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)
        print(f"Created: {channel_name} in {cat_name}")
        await asyncio.sleep(1) # Delay between creation and message
        
        package = random.choice(SERVICES[cat_name])
        payment = random.choice(PAYMENT_METHODS)
        
        embed = discord.Embed(title="📝 **Order Confirmed**", color=0x2ECC71, timestamp=datetime.now())
        item_label = "📦 Service" if "Gifting" in cat_name else "🛒 Item"
        embed.add_field(name=item_label, value=f"**{package}**", inline=False)
        embed.add_field(name="💳 Payment Method", value=f"**{payment}**", inline=True)
        
        if random.random() > 0.5:
            notes = random.choice(["I paid with CIH, check proof.", f"Riot ID: {user_name}#EUW", "Waiting for delivery...", "Fast please!", "Thank you."])
            embed.add_field(name="🗒️ Notes / Info", value=notes, inline=False)
            
        embed.set_author(name=user_name)
        embed.set_footer(text="Please wait for an admin to handle your order.")
        
        await channel.send(embed=embed)
        await asyncio.sleep(0.5)
        await channel.send(f"Support will process it shortly.")
    except Exception as e:
        print(f"Error creating ticket: {e}")

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    if not client.guilds:
        print("No guilds found.")
        await client.close()
        return
        
    guild = client.guilds[0]
    print(f"Targeting: {guild.name}")
    
    categories_to_fill = ["Valorant Orders", "Gifting Orders", "Valorant Points"]
    
    for cat_name in categories_to_fill:
        category = discord.utils.get(guild.categories, name=cat_name)
        if not category:
            try:
                overwrites = {guild.default_role: discord.PermissionOverwrite(view_channel=False)}
                category = await guild.create_category(cat_name, overwrites=overwrites)
                print(f"Created category: {cat_name}")
                await asyncio.sleep(1)
            except Exception as e:
                print(f"Error creating category {cat_name}: {e}")
                continue
        
        num_tickets = random.randint(3, 5) # Slightly fewer tickets to avoid rate limit/server load
        for _ in range(num_tickets):
            await create_fake_ticket(guild, category, cat_name)
            await asyncio.sleep(1.5) # More substantial delay between tickets
            
    print("\n✅ All fake tickets created successfully!")
    await client.close()


if __name__ == "__main__":
    client.run(TOKEN)
