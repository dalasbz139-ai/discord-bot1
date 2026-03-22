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
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)

class TicketSystemView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="📩 Open Ticket", style=discord.ButtonStyle.green, custom_id="create_ticket_btn"))

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    guild = client.guilds[0]
    bot_dir = os.path.dirname(os.path.abspath(__file__))
    karys_image_path = os.path.join(bot_dir, "karys.png")

    # Get channels by their pretty names (using partial matching)
    def find_ch(name):
        return discord.utils.get(guild.text_channels, name=name)

    rules_ch = find_ch("📜・rules")
    pay_ch = find_ch("💳・payment-methods")
    gift_ch = find_ch("🎁・valorant-gifting")
    panel_ch = find_ch("📩・open-ticket")

    # Clean existing messages in those channels (optional but better for "looking good")
    # Actually, let's just send new ones or headers.
    
    if panel_ch:
        embed = discord.Embed(
            title="🛒 **KARYS SHOP | SUPPORT & ORDERS**",
            description=(
                "**Welcome to Karys Shop!** 🌟\nمرحباً بكم في متجر كاريس! 🇲🇦\n\n"
                "**Open a ticket for:**\n"
                "💸 **Buying & Selling** (Accounts, VP, Nitro)\n"
                "🛠️ **Support & Assistance**\n\n"
                "*Click the button below to start!* 📩"
            ),
            color=0xFF0000
        )
        if os.path.exists(karys_image_path):
            file = discord.File(karys_image_path, filename="karys.png")
            embed.set_thumbnail(url="attachment://karys.png")
            await panel_ch.send(embed=embed, file=file, view=TicketSystemView())
        print("Updated panel.")

    if rules_ch:
        embed = discord.Embed(title="📜〢─ RULES & TERMS ─〢📜", color=0xFF0000)
        embed.add_field(name="🔐 TRUST", value="🛡️ Only buy from verified admins.\n👤 Ignore fake staff accounts.", inline=True)
        embed.add_field(name="⏱️ DELIVERY", value="⚡ 1–5 mins after payment.", inline=True)
        embed.add_field(name="💸 REFUNDS", value="❌ No refunds after delivery.", inline=False)
        embed.set_footer(text="Karys Shop | Quality and Speed ⚡")
        await rules_ch.send(embed=embed)
        print("Updated rules.")

    print("Pretty Finalization Complete.")
    await client.close()

if __name__ == "__main__":
    client.run(TOKEN)
