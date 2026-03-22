import discord
import os
import asyncio
from dotenv import load_dotenv
import sys
from datetime import datetime

load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)

PRICE_LIST = {
    "1000": {"usd": 5.0, "dh": 50, "stock": False},
    "5000": {"usd": 25.0, "dh": 250, "stock": False},
    "10000": {"usd": 50.0, "dh": 500, "stock": True},
    "11000": {"usd": 55.0, "dh": 550, "stock": True},
    "12000": {"usd": 60.0, "dh": 600, "stock": True},
    "13000": {"usd": 65.0, "dh": 650, "stock": True},
    "14000": {"usd": 70.0, "dh": 700, "stock": True},
    "15000": {"usd": 75.0, "dh": 750, "stock": True},
    "16000": {"usd": 80.0, "dh": 800, "stock": True},
    "18000": {"usd": 90.0, "dh": 900, "stock": True},
    "20000": {"usd": 105.0, "dh": 1050, "stock": True},
    "100000": {"usd": 455.0, "dh": 4550, "stock": True}
}

class TicketSystemView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="📩 Open Ticket", style=discord.ButtonStyle.green, custom_id="create_ticket_btn"))

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    for guild in client.guilds:
        print(f"Finalizing guild: {guild.name}")
        
        # 1. Post Prices
        prices_ch = discord.utils.get(guild.text_channels, name="prices")
        if prices_ch:
            embed = discord.Embed(
                title="🔻 Valorant Points Price List 🔻",
                color=0xFF0000
            )
            embed.add_field(name="🎮 Available on:", value="PlayStation 5 | Xbox | PC", inline=False)
            
            price_text = ""
            for points, info in PRICE_LIST.items():
                points_int = int(points)
                status = " (Out of Stock)" if not info['stock'] else ""
                price_text += f"{points_int:,} VP → {info['usd']} $ │ {info['dh']} dh{status}\n"
            
            embed.add_field(name="💰 Prices", value=price_text, inline=False)
            embed.set_footer(text="Karys Shop | Trusted Valorant Points Provider")
            
            bot_dir = os.path.dirname(os.path.abspath(__file__))
            image_path = os.path.join(bot_dir, "karys.png")
            if os.path.exists(image_path):
                file = discord.File(image_path, filename="karys.png")
                embed.set_image(url="attachment://karys.png")
                await prices_ch.send(embed=embed, file=file)
            else:
                await prices_ch.send(embed=embed)
            print("Posted prices.")

        # 2. Post Ticket Panel
        panel_ch = discord.utils.get(guild.text_channels, name="ticket-panel")
        if panel_ch:
            embed = discord.Embed(
                title="🛒 **KARYS SHOP | SUPPORT & ORDERS**",
                description=(
                    "**Welcome to Karys Shop!** 🌟\nمرحباً بكم في متجر كاريس! 🇲🇦\n\n"
                    "**Open a ticket for:**\n"
                    "💸 **Buying & Selling** (Accounts, Points, Nitro)\n"
                    "🛠️ **Support & Assistance**\n\n"
                    "*Click the button below to start your transaction!* 📩"
                ),
                color=0xFF0000
            )
            image_path = os.path.join(bot_dir, "karys.png")
            if os.path.exists(image_path):
                file = discord.File(image_path, filename="karys.png")
                embed.set_thumbnail(url="attachment://karys.png")
                await panel_ch.send(embed=embed, file=file, view=TicketSystemView())
            else:
                await panel_ch.send(embed=embed, view=TicketSystemView())
            print("Posted ticket panel.")

        # 3. Rules
        rules_ch = discord.utils.get(guild.text_channels, name="rules")
        if rules_ch:
            embed = discord.Embed(title="📜 RULES — BUYING TERMS", color=0xFF0000)
            embed.add_field(name="🔐 Security & Trust", value="🛡️ Purchases must be made only through verified admins.\n👤 Anyone claiming staff without official confirmation is a scammer.", inline=False)
            embed.add_field(name="⏱️ Order Processing", value="⚡ Orders delivered within 1–5 minutes after payment confirmation.", inline=False)
            embed.add_field(name="💸 Refund Policy", value="❌ No refunds once the product has been delivered.", inline=False)
            await rules_ch.send(embed=embed)
            print("Posted rules.")

    print("Setup finalized. Closing.")
    await client.close()

if __name__ == "__main__":
    client.run(TOKEN)
