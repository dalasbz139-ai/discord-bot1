import discord
import os
import asyncio
from dotenv import load_dotenv
import sys
from datetime import datetime

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)

class TicketButton(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__()
        # Link to the specific channel if needed, or just a dummy
        # In bot.py, this links to the instructions/ticket channel
        self.add_item(discord.ui.Button(label="Open a Ticket", style=discord.ButtonStyle.link, url=f"https://discord.com/channels/{guild_id}/1485141935210365171", emoji="🎟️"))

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    guild = client.guilds[0] # Assume first guild
    bot_dir = os.path.dirname(os.path.abspath(__file__))
    karys_image_path = os.path.join(bot_dir, "karys.png")

    # 1. RULES (📚 INFO > rules)
    rules_ch = discord.utils.get(guild.text_channels, name="rules")
    if rules_ch:
        embed = discord.Embed(title="📜 RULES — BUYING TERMS", color=0xFF0000)
        embed.add_field(name="🔐 Security & Trust", value="🛡️ Purchases must be made only through verified admins or sellers.\n👤 Anyone claiming to be staff without official confirmation should be ignored.", inline=False)
        embed.add_field(name="⏱️ Order Processing", value="⚡ Orders are delivered within 1 to 5 minutes after payment confirmation.", inline=False)
        embed.add_field(name="💸 Refund Policy", value="❌ No refunds will be issued once the product has been successfully delivered.", inline=False)
        embed.add_field(name="🚫 Liability", value="📩 The server is not responsible for scams via private messages or fake accounts.\n🔎 Always verify the official Discord tag before sending payment.", inline=False)
        embed.add_field(name="🚨 Important Warning", value="🎁 Do not trust fake discounts, giveaways, or edited screenshots.", inline=False)
        embed.add_field(name="🏦 Secure Payments", value="✅ Payments must be made only through official payment channels or verified shop contacts.", inline=False)
        embed.set_footer(text="Karys Shop")
        await rules_ch.send(embed=embed)
        print("Updated rules.")

    # 2. PAYMENT METHODS (🛒 KARYS SHOP > payment-methods)
    pay_ch = discord.utils.get(guild.text_channels, name="payment-methods")
    if pay_ch:
        embed = discord.Embed(
            title="💳 **SECURE PAYMENT METHODS** | طرق الدفع",
            description="To complete your purchase, please choose a payment method below and **open a ticket**.\nلإتمام عملية الشراء، اختر طريقة الدفع وافتح تذكرة.",
            color=0xFF0000 
        )
        embed.add_field(name="🏦 **Bank Transfer** (تحويل بنكي)", value="> **CIH Bank**\n> **BMCE Bank**\n> **Attijariwafa Bank**\n> **Barid Bank**\n```fix\nOpen a ticket to receive RIB / Account Number\nافتح تذكرة للحصول على رقم الحساب البنكي\n```", inline=False)
        embed.add_field(name="🪙 **Crypto & E-Wallets**", value="> **Binance Pay** (USDT)\n> **USDT (TRC20)**\n> **PayPal** (FnF Only)\n```fix\nOpen a ticket to receive Wallet / Email\nافتح تذكرة للحصول على المحفظة أو البريد\n```", inline=False)
        embed.add_field(name="📝 **How to Order?** (كيفاش تشري؟)", value="1️⃣ **Open Ticket** 📩 : Click the button in <#ticket-panel>.\n2️⃣ **Selection** 🗣️ : Tell us payment method + Product.\n3️⃣ **Payment** 💸 : Send the money & Screenshot.\n4️⃣ **Delivery** 🚀 : Receive your product instantly!", inline=False)
        embed.set_footer(text="Karys Shop | Trusted & Secure 🔒")
        if os.path.exists(karys_image_path):
            file = discord.File(karys_image_path, filename="karys.png")
            embed.set_thumbnail(url="attachment://karys.png")
            await pay_ch.send(embed=embed, file=file, view=TicketButton(guild.id))
        else:
            await pay_ch.send(embed=embed, view=TicketButton(guild.id))
        print("Updated payments.")

    # 3. VALORANT GIFTING (🛒 KARYS SHOP > gift)
    gift_ch = discord.utils.get(guild.text_channels, name="gift")
    if gift_ch:
        embed = discord.Embed(
            title="🎁 OFFICIAL GIFTING SERVICE",
            description="**Get your favorite Valorant skins & bundles directly in-game!**\nWe offer a safe and instant gifting service.",
            color=0xFD4556
        )
        embed.add_field(name="🆔 Riot IDs to Add (Select your region)", value="**🇪🇺 Europe:** `DALAS L7#9999`\n**🇹🇷 Turkey:** `DALAS L7#BOSS`\n\n*Send a friend request to the correct account to start.*", inline=False)
        embed.add_field(name="🇺🇸 How it works", value="**1️⃣ Add Friend:** Send a request to the ID above.\n**2️⃣ Wait 7 Days:** Wait the mandatory 7-day period (Riot Rule).\n**3️⃣ Payment:** Pay via CIH / Attijari / Crypto.\n**4️⃣ Receive:** Get your skin/bundle instantly!", inline=False)
        embed.add_field(name="🇲🇦 طريقة العمل", value="**1️⃣ طلب صداقة:** أرسل طلب للآيدي الموضح أعلاه.\n**2️⃣ الانتظار:** انتظر مدة 7 أيام (قانون اللعبة).\n**3️⃣ الدفع:** ادفع عبر CIH / التجاري / Crypto.\n**4️⃣ الاستلام:** استلم هديتك فوراً!", inline=False)
        embed.set_footer(text="Karys Shop | Valorant Gifting Service")
        if os.path.exists(karys_image_path):
            file = discord.File(karys_image_path, filename="karys.png")
            embed.set_thumbnail(url="attachment://karys.png")
            await gift_ch.send(embed=embed, file=file, view=TicketButton(guild.id))
        else:
            await gift_ch.send(embed=embed, view=TicketButton(guild.id))
        print("Updated gifting.")

    print("Finalize Setup v2 complete.")
    await client.close()

if __name__ == "__main__":
    client.run(TOKEN)
