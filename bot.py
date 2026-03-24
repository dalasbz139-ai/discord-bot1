import discord
from discord.ext import commands, tasks
import asyncio
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
import json
import random
from typing import Literal
import aiohttp
import re
import io
# Load environment variables
load_dotenv()

# Initialize bot with intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)
import uuid
INSTANCE_ID = str(uuid.uuid4())[:8]


# Price list data
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

VBUCKS_PRICES = {
    "10000": "400",
    "12000": "480",
    "15000": "600",
    "25000": "1000",
    "50000": "1800"
}

# --- Data Management ---
def load_data(filename):
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_data(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

# Load data on startup
invites_data = load_data('invites.json') # Structure: {"user_id": {"regular": 0, "fake": 0, "bonus": 0, "leaves": 0}}
giveaways_data = load_data('giveaways.json')
invite_cache = {} # Cache for tracking invite uses

def get_invites(user_id):
    user_id = str(user_id)
    if user_id not in invites_data:
        invites_data[user_id] = {"regular": 0, "fake": 0, "bonus": 0, "leaves": 0}
    
    data = invites_data[user_id]
    total = (data["regular"] + data["bonus"]) - (data["leaves"] + data["fake"])
    return total if total > 0 else 0



# --- Rock Paper Scissors Game ---
class RPSView(discord.ui.View):
    def __init__(self, user: discord.Member):
        super().__init__(timeout=60)
        self.user = user

    def determine_winner(self, player, bot):
        if player == bot:
            return "Tie!"
        elif (player == "rock" and bot == "scissors") or \
             (player == "paper" and bot == "rock") or \
             (player == "scissors" and bot == "paper"):
            return "You win!"
        else:
            return "I win!"

    async def play(self, interaction: discord.Interaction, player_choice: str):
        if interaction.user != self.user:
            await interaction.response.send_message("This isn't your game!", ephemeral=True)
            return

        bot_choice = random.choice(["rock", "paper", "scissors"])
        emojis = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
        
        result = self.determine_winner(player_choice, bot_choice)
        
        embed = discord.Embed(
            title="Rock Paper Scissors",
            description=f"You chose {emojis[player_choice]}\nI chose {emojis[bot_choice]}\n\n**{result}**",
            color=0x3498DB if "win" in result.lower() else 0xE74C3C
        )
        
        for item in self.children:
            item.disabled = True
            
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="rock", style=discord.ButtonStyle.secondary, emoji="🪨")
    async def btn_rock(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.play(interaction, "rock")

    @discord.ui.button(label="paper", style=discord.ButtonStyle.blurple, emoji="📄")
    async def btn_paper(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.play(interaction, "paper")

    @discord.ui.button(label="scissors", style=discord.ButtonStyle.danger, emoji="✂️")
    async def btn_scissors(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.play(interaction, "scissors")


# --- Giveaway System ---
class GiveawayJoinButton(discord.ui.View):
    def __init__(self, message_id, required_invites):
        super().__init__(timeout=None)
        self.message_id = str(message_id)
        self.required_invites = required_invites

    @discord.ui.button(label="🎉 Join Giveaway", style=discord.ButtonStyle.green, custom_id="join_giveaway_btn")
    async def join_giveaway(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Determine giveaway ID from message
        giveaway_id = str(interaction.message.id)
        
        # Check if giveaway exists
        if giveaway_id not in giveaways_data:
            await interaction.response.send_message("❌ This giveaway has ended or does not exist.", ephemeral=True)
            return

        giveaway = giveaways_data[giveaway_id]
        
        if giveaway["ended"]:
            await interaction.response.send_message("❌ This giveaway has already ended.", ephemeral=True)
            return

        user_id = str(interaction.user.id)
        
        # Check if already joined
        if user_id in giveaway["participants"]:
            await interaction.response.send_message("⚠️ You have already joined this giveaway!", ephemeral=True)
            return

        # Check invites
        user_invites = get_invites(user_id)
        if user_invites < self.required_invites:
            await interaction.response.send_message(f"❌ You need **{self.required_invites}** invites to join. You currently have **{user_invites}**.", ephemeral=True)
            return

        # Add to participants
        giveaway["participants"].append(user_id)
        save_data('giveaways.json', giveaways_data)
        
        # Update Embed count
        embed = interaction.message.embeds[0]
        field_index = -1
        for i, field in enumerate(embed.fields):
            if "Entries" in field.name:
                field_index = i
                break
        
        if field_index != -1:
            embed.set_field_at(field_index, name="👥 Entries", value=str(len(giveaway["participants"])), inline=True)
            await interaction.message.edit(embed=embed)

        await interaction.response.send_message(f"✅ You successfully joined the giveaway! (Invites: {user_invites})", ephemeral=True)

class TicketButton(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__()
        # Link to the specific channel
        url = f"https://discord.com/channels/{guild_id}/1485141935210365171"
        self.add_item(discord.ui.Button(label="Open a Ticket", style=discord.ButtonStyle.link, url=url, emoji="🎟️"))

class TicketAdminView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="� Reopen Ticket", style=discord.ButtonStyle.green, custom_id="reopen_ticket_btn")
    async def reopen_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        # Get Tickets Category
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="Tickets")
        if not category:
            category = await guild.create_category("Tickets")
            
        await interaction.channel.edit(category=category)
        
        # Restore user permissions
        # We need to find the user from the channel name or topic, but easier:
        # Just restore permissions for the specific user found in overwrites
        for target, overwrite in interaction.channel.overwrites.items():
            if isinstance(target, discord.Member) and target != guild.me:
                # Use view_channel for d.py 2.0+
                await interaction.channel.set_permissions(target, view_channel=True, send_messages=True, read_message_history=True)
                
                # Try to rename, but don't fail if rate limited
                try:
                    await interaction.channel.edit(name=f"ticket-{target.name}")
                except Exception as e:
                    print(f"[WARNING] Could not rename channel on reopen: {e}")
                    
                await interaction.channel.send(f"🔓 Ticket reopened! Welcome back {target.mention}")
                return
        
        await interaction.followup.send("✅ Ticket reopened (User not found in overwrites)", ephemeral=True)

    @discord.ui.button(label="⛔ Delete Ticket", style=discord.ButtonStyle.red, custom_id="delete_ticket_btn")
    async def delete_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("⛔ Deleting ticket in 5 seconds...", ephemeral=True)
        await asyncio.sleep(5)
        await interaction.channel.delete()

    @discord.ui.button(label="📝 Force Rename", style=discord.ButtonStyle.secondary, custom_id="force_rename_btn", emoji="📝")
    async def force_rename(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Admin tool to retry renaming if rate limited
        try:
             # Sanitize owner name query
             new_name = f"closedorder-{interaction.channel.name.split('-')[-1]}"
             # Try to find original owner from embed if possible, but channel name suffix is safest fallback
             
             await interaction.response.defer()
             await interaction.channel.edit(name=new_name)
             await interaction.followup.send(f"✅ Renamed to {new_name}", ephemeral=True)
        except Exception as e:
             await interaction.followup.send(f"❌ Failed to rename: {e}\n(Discord limits renames to 2 per 10 mins. Try again later.)", ephemeral=True)

class TicketCloseConfirmationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.red, custom_id="confirm_close_btn", emoji="🔒")
    async def confirm_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("⛔ Closing ticket in 5 seconds...", ephemeral=False)
        await asyncio.sleep(5)
        
        channel = interaction.channel
        guild = interaction.guild
        
        # 0. Extract Info (Owner & Order) before closing
        ticket_owner = "Unknown"
        order_info = "General Support / No Order Found"
        
        # Try to find owner from channel name or permissions
        # Best guess: Find the user who has view permissions and isn't a bot/admin
        # OR scan chat for the welcome message mention
        
        # Scan chat for Order Embed to get valid info
        try:
            async for msg in channel.history(limit=50, oldest_first=True):
                # Check for Welcome Mention for owner
                if not ticket_owner or ticket_owner == "Unknown":
                    if msg.mentions and not msg.author.bot:
                         # First human mention might be owner? No, bot mentions user in welcome.
                         pass
                
                # Check for Bot's Embeds
                if msg.author.id == interaction.client.user.id and msg.embeds:
                    embed = msg.embeds[0]
                    # Check for Order
                    if "Order" in (embed.title or ""):
                        for field in embed.fields:
                            if field.name in ["🛒 Item", "📦 Service"]:
                                order_info = field.value
                        # Also get author if available
                        if embed.author:
                            ticket_owner = embed.author.name
                    
                    # Check for Welcome to grab owner if not found yet
                    if "Welcome" in (embed.title or "") and "Ticket" not in (embed.title or ""):
                         # "👋 Welcome username!"
                         if "Welcome" in embed.title:
                             ticket_owner = embed.title.replace("👋 Welcome ", "").replace("!", "")

        except:
             pass

        try:
            try:
                await interaction.message.delete()
            except:
                pass
            
            # Get Logs Category — fill existing first, create new only if all full
            # Max 50 tickets per category. Categories: LOGS 1, LOGS 2, LOGS 3...
            MAX_PER_CATEGORY = 50
            target_category = None

            # Step 1: Find existing LOGS categories and pick first one with space
            existing_logs = []
            for cat in guild.categories:
                if "LOGS" in cat.name.upper():
                    # Try to extract number using regex
                    match = re.search(r'LOGS\s*(\d+)', cat.name, re.IGNORECASE)
                    if match:
                        num = int(match.group(1))
                        existing_logs.append((num, cat))
            
            existing_logs.sort(key=lambda x: x[0])

            for num, cat in existing_logs:
                if len(cat.channels) < MAX_PER_CATEGORY:
                    target_category = cat
                    break

            # Step 2: If all full or none exist, create a new LOGS category
            if not target_category:
                next_num = (existing_logs[-1][0] + 1) if existing_logs else 1
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(view_channel=False)
                }
                target_category = await guild.create_category(f"🛡️ LOGS {next_num}", overwrites=overwrites)


            # Step 1: Move category (Critical)
            await channel.edit(category=target_category)
            
            # Step 2: Remove permissions (Security)
            for target, overwrite in channel.overwrites.items():
                if isinstance(target, discord.Member) and target != guild.me:
                    await channel.set_permissions(target, view_channel=False, send_messages=False, read_message_history=False)

            # Step 3: Send Enhanced Embed (Controls + Info)
            embed = discord.Embed(
                title="🔒 **Ticket Closed**",
                color=0xFF0000,
                timestamp=datetime.now()
            )
            embed.add_field(name="👤 Ticket Owner", value=f"**{ticket_owner}**", inline=True)
            embed.add_field(name="🛡️ Closed By", value=interaction.user.mention, inline=True)
            embed.add_field(name="📝 Order Info", value=order_info, inline=False)
            embed.set_footer(text="Manage this ticket below ⬇️")
            
            await channel.send(embed=embed, view=TicketAdminView())
            
            # Step 4: Rename Channel (Cosmetic - Low Priority)
            # We put this last so if it fails (rate limit), the ticket is still closed and usable by admins
            try:
                # Sanitize owner name (remove spaces/special chars)
                safe_owner = "unknown"
                if ticket_owner and ticket_owner != "Unknown":
                    safe_owner = "".join(c for c in ticket_owner if c.isalnum()).lower()
                else:
                    # Fallback to channel name suffix
                    safe_owner = channel.name.split('-')[-1]
                
                # "closedorder" stuck together as requested + Date
                date_str = datetime.now().strftime("%d%m") # DayMonth e.g. 1302
                new_name = f"closedorder-{safe_owner}-{date_str}"
                await channel.edit(name=new_name[:100])
            except Exception as e:
                print(f"[WARNING] Rename failed (Rate Limit?): {e}")
            
        except Exception as e:
            print(f"[ERROR] processing ticket close: {e}")
            import traceback
            traceback.print_exc()
            try:
                await interaction.followup.send(f"❌ Error closing ticket: {e}", ephemeral=True)
            except:
                pass

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.gray, custom_id="cancel_close_btn")
    async def cancel_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        try:
            await interaction.message.delete()
        except:
            pass

class OrderModal(discord.ui.Modal):
    def __init__(self, service_name, title="Order Details"):
        super().__init__(title=title)
        self.service_name = service_name
        
        self.quantity = discord.ui.TextInput(
            label="Quantity / Amount",
            placeholder="Ex: 1000 VP, 1 Year Nitro, etc...",
            required=True,
            style=discord.TextStyle.short
        )
        self.notes = discord.ui.TextInput(
            label="Additional Notes / Payment Method",
            placeholder="Ex: Paying with CIH, I need fast delivery...",
            required=False,
            style=discord.TextStyle.long
        )
        self.add_item(self.quantity)
        self.add_item(self.notes)

    async def on_submit(self, interaction: discord.Interaction):
        # Update the ticket name to reflect the order (optional)
        try:
            # Normalize service name for channel name
            safe_service = self.service_name.lower().replace(' ', '-').replace('/', '-').replace('v-bucks', 'vbucks')
            new_name = f"order-{safe_service}-{interaction.user.name}"
            # Truncate to 100 chars just in case
            await interaction.channel.edit(name=new_name[:100])
        except:
            pass # Ignore rename errors

        embed = discord.Embed(
            title="📝 **New Order Request**",
            color=0xF1C40F, # Gold/Yellow for order
            timestamp=datetime.now()
        )
        embed.add_field(name="📦 Service", value=f"**{self.service_name}**", inline=True)
        embed.add_field(name="🔢 Quantity", value=str(self.quantity.value), inline=True)
        if self.notes.value:
            embed.add_field(name="🗒️ Notes", value=str(self.notes.value), inline=False)
        
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_footer(text="Wait for support to process your order.")

        await interaction.response.send_message(embed=embed)
        # Ping support/admin here if needed
        await interaction.channel.send(f"{interaction.user.mention} Thank you! Support will be with you shortly.")

async def process_package_order(interaction: discord.Interaction, item_str, payment_method, notes=None):
    try:
        # Rename channel to order
        safe_item = item_str.split(':')[0].lower().replace(' ', '-').replace('v-bucks', 'vbucks')
        await interaction.channel.edit(name=f"order-{safe_item}-{interaction.user.name}"[:100])
        
        # Move to Category
        guild = interaction.guild
        category_name = "Orders" # Default
        
        if "Gifting" in item_str:
            category_name = "Gifting Orders"
        elif "VP" in item_str or "Valorant" in item_str:
            category_name = "Valorant Points"
            
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False)
            }
            category = await guild.create_category(category_name, overwrites=overwrites)
        
        await interaction.channel.edit(category=category)
        
    except Exception as e:
        print(f"Error moving/renaming: {e}")
        pass

    # Enable writing for user after order
    try:
        await interaction.channel.set_permissions(interaction.user, view_channel=True, send_messages=True, read_message_history=True)
    except Exception as e:
        print(f"Error setting permissions after order: {e}")

    embed = discord.Embed(title="📝 **Order Confirmed**", color=0x2ECC71, timestamp=datetime.now())
    embed.add_field(name="🛒 Item", value=f"**{item_str}**", inline=False)
    embed.add_field(name="💳 Payment Method", value=f"**{payment_method}**", inline=True)
    
    if notes:
        embed.add_field(name="🗒️ Notes / Info", value=str(notes), inline=False)
    
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
    embed.set_footer(text="Please wait for an admin to handle your order.")
    
    # Check if interaction is deferred or responded to
    if interaction.response.is_done():
        await interaction.followup.send(embed=embed)
    else:
        await interaction.response.send_message(embed=embed)
        
    await interaction.channel.send(f"{interaction.user.mention} Order received! Support will process it shortly.")


class PackageSelect(discord.ui.Select):
    def __init__(self, service_type, options):
        self.service_type = service_type
        super().__init__(placeholder=f"Select {service_type} Package...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        package = self.values[0]

        # Check stock for Valorant Points
        if self.service_type == "VP":
            # Extract amount from label (e.g., "1,000 VP" -> "1000")
            amount_str = package.replace(" VP", "").replace(",", "")
            
            if amount_str in PRICE_LIST and not PRICE_LIST[amount_str]["stock"]:
                await interaction.response.send_message(
                    "❌ **This package is currently Out of Stock!**\nPlease select a different package that is available.",
                    ephemeral=True
                )
                return

        # Prepare to send Image and Payment view
        embed = discord.Embed(
            title="💳 Payment Method",
            description=f"You selected: **{self.service_type} - {package}**\nPlease select your payment method below:",
            color=0x2ECC71
        )
        view = PaymentMethodView(f"{self.service_type}: {package}")
        
        # Check if it's a specific Gifting bundle to show its image
        bot_dir = os.path.dirname(os.path.abspath(__file__))
        image_path = None
        
        if self.service_type == "Gifting":
            if "VCT 2026 SEASON" in package:
                image_path = os.path.join(bot_dir, "vct2026.png")
            elif "LUNAR 26" in package:
                image_path = os.path.join(bot_dir, "lunar26.png")
            elif "QUACKED SERIES" in package:
                image_path = os.path.join(bot_dir, "quacked.png")
                
        if image_path and os.path.exists(image_path):
            file = discord.File(image_path, filename=os.path.basename(image_path))
            embed.set_image(url=f"attachment://{os.path.basename(image_path)}")
            await interaction.response.send_message(embed=embed, file=file, view=view, ephemeral=True)
        else:
            # Open Payment Method Selection (No image or image not found)
            await interaction.response.send_message(
                embed=embed, 
                view=view,
                ephemeral=True
            )

class PackageOrderModal(discord.ui.Modal):
    def __init__(self, title_str, payment_method):
        super().__init__(title="Confirm Order Details")
        self.item_str = title_str
        self.payment_method = payment_method
        
        # Payment method is already selected, so we just ask for notes/riot id
        self.notes = discord.ui.TextInput(
            label="Questions / Notes (أسئلة / ملاحظات)",
            placeholder="Account Email / Riot ID / Special Requests...",
            required=False,
            style=discord.TextStyle.long
        )
        self.add_item(self.notes)

    async def on_submit(self, interaction: discord.Interaction):
        try:
             # Rename channel to order
            safe_item = self.item_str.split(':')[0].lower().replace(' ', '-').replace('v-bucks', 'vbucks')
            await interaction.channel.edit(name=f"order-{safe_item}-{interaction.user.name}"[:100])
            
            # Move to Category
            guild = interaction.guild
            category_name = "Orders" # Default
            
            if "Gifting" in self.item_str:
                category_name = "Gifting Orders"
            elif "VP" in self.item_str or "Valorant" in self.item_str:
                category_name = "Valorant Points"
                
            category = discord.utils.get(guild.categories, name=category_name)
            if not category:
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(view_channel=False)
                }
                category = await guild.create_category(category_name, overwrites=overwrites)
            
            await interaction.channel.edit(category=category)
            
        except Exception as e:
            print(f"Error moving/renaming: {e}")
            pass

        # Enable writing for user after order
        try:
            await interaction.channel.set_permissions(interaction.user, view_channel=True, send_messages=True, read_message_history=True)
        except Exception as e:
            print(f"Error setting permissions after order: {e}")

        embed = discord.Embed(title="📝 **Order Confirmed**", color=0x2ECC71, timestamp=datetime.now())
        embed.add_field(name="🛒 Item", value=f"**{self.item_str}**", inline=False)
        embed.add_field(name="💳 Payment Method", value=f"**{self.payment_method}**", inline=True)
        
        if self.notes.value:
            embed.add_field(name="🗒️ Notes / Info", value=str(self.notes.value), inline=False)
        
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_footer(text="Please wait for an admin to handle your order.")
        
        await interaction.response.send_message(embed=embed)
        await interaction.channel.send(f"{interaction.user.mention} Order received! Support will process it shortly.")

class PaymentSelect(discord.ui.Select):
    def __init__(self, package_info):
        self.package_info = package_info
        options = [
            discord.SelectOption(label="CIH Bank", emoji="🏦", description="Bank Transfer"),
            discord.SelectOption(label="BMCE Bank", emoji="🏦", description="Bank Transfer"),
            discord.SelectOption(label="Cash Plus", emoji="💸", description="Cash Transfer"),
            discord.SelectOption(label="Binance (USDT)", emoji="🪙", description="Crypto Payment"),
        ]
        super().__init__(placeholder="Select Payment Method...", min_values=1, max_values=1, options=options)


    async def callback(self, interaction: discord.Interaction):
        payment_method = self.values[0]
        # Bypass modal and process order directly
        await process_package_order(interaction, self.package_info, payment_method)
        # await interaction.response.send_modal(PackageOrderModal(self.package_info, payment_method))

class PaymentMethodView(discord.ui.View):
    def __init__(self, package_info):
        super().__init__(timeout=60)
        self.add_item(PaymentSelect(package_info))

class GiftingButtonView(discord.ui.View):
    def __init__(self, bundle_name, bundle_vp, price_dh, price_usd):
        super().__init__(timeout=None)
        self.bundle_name = bundle_name
        self.bundle_vp = bundle_vp
        self.price_dh = price_dh
        self.price_usd = price_usd

    @discord.ui.button(label="🛒 Order", style=discord.ButtonStyle.green, custom_id="order_gifting_bundle")
    async def order_bundle(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Format the item string to include the price for the final order embed
        item_str = f"Gifting: {self.bundle_name} ({self.bundle_vp:,} VP) | {self.price_usd} $ | {self.price_dh} DH"
        
        embed = discord.Embed(
            title="💳 Payment Method",
            description=f"You selected: **{self.bundle_name}**\nPlease select your payment method below:",
            color=0x2ECC71
        )
        view = PaymentMethodView(item_str)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class ServiceSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Valorant Points", emoji="<:vp:1466944483504427008>", description="VP Top-up for all regions", value="vp"),
            discord.SelectOption(label="Valorant Gifting", emoji="🎁", description="Skins & Bundles Gifting Service", value="gifting"),
            discord.SelectOption(label="Other / Support", emoji="❓", description="General questions or other services", value="other")
        ]
        super().__init__(placeholder="Select the service you want...", min_values=1, max_values=1, options=options, custom_id="service_select_menu")

    async def callback(self, interaction: discord.Interaction):
        service = self.values[0]

        # Disable the dropdown to prevent changing selection
        self.disabled = True
        self.placeholder = "Service Selected"
        await interaction.message.edit(view=self.view)
        
        if service == "vp":
            # Show VP Options
            embed = discord.Embed(title="<:vp:1466944483504427008> **Valorant Points Packages**", description="Select your package below:", color=0xFF4654)
            
            # Full List from PRICE_LIST
            options = []
            # Sort by price (int key)
            sorted_prices = sorted(PRICE_LIST.items(), key=lambda x: int(x[0]))
            
            for points, info in sorted_prices:
                points_int = int(points)
                status = " (Out of Stock)" if not info['stock'] else ""
                # Format: 1,000 VP
                label = f"{points_int:,} VP"
                # Description: 5.0 $ | 50 dh (Out of Stock)
                description = f"{info['usd']} $ | {info['dh']} dh{status}"
                
                options.append(discord.SelectOption(
                    label=label, 
                    description=description, 
                    emoji="<:vp:1466944483504427008>"
                ))
            
            # Split into two selects if needed, but max is 25 options, so one is fine.
            view = discord.ui.View()
            view.add_item(PackageSelect("VP", options))
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        elif service == "gifting":
            embed = discord.Embed(
                title="🎁 **OFFICIAL GIFTING SERVICE**",
                description="**Get your favorite Valorant skins & bundles directly in-game!**\nWe offer a safe and instant gifting service.",
                color=0xFF4654
            )
            
            embed.add_field(
                name="🆔 Riot IDs to Add (اختر منطقتك)",
                value=(
                    "**🇪🇺 Europe:** `DALAS L7#9999`\n"
                    "**🇹🇷 Turkey:** `DALAS L7#BOSS`\n\n"
                    "*Send a friend request to the correct account to start.*"
                ),
                inline=False
            )
            
            embed.add_field(
                name="⚠️ Important Note / ملاحظة مهمة",
                value="**You must wait 7 days after adding us to receive the gift (Game Rule).**\n**يجب الانتظار 7 أيام بعد إضافة الحساب لاستلام الهدية (قانون اللعبة).**",
                inline=False
            )
            
            embed.set_footer(text="Karys Shop | Valorant Gifting Service")
            
            try:
                # Move to Gifting Orders Category if exists
                guild = interaction.guild
                category = discord.utils.get(guild.categories, name="Gifting Orders")
                if not category:
                     overwrites = {
                        guild.default_role: discord.PermissionOverwrite(view_channel=False)
                     }
                     category = await guild.create_category("Gifting Orders", overwrites=overwrites)
                await interaction.channel.edit(category=category)
            except:
                pass
                
            # Send intro Embed first
            await interaction.response.send_message(embed=embed, ephemeral=False)
            
            # New Bundles Added
            bundles = [
                {"name": "BLACKTHORN BUNDLE", "vp": 8700, "price_dh": 435.0, "price_usd": 43.50, "image": "blackthorn_bundle.png"},
                {"name": "BLACKTHORN BLADES", "vp": 4350, "price_dh": 217.5, "price_usd": 21.75, "image": "blackthorn_blades.png"},
                {"name": "BLACKTHORN VANDAL", "vp": 2175, "price_dh": 108.75, "price_usd": 10.88, "image": "blackthorn_vandal.png"},
                {"name": "BLACKTHORN MARSHAL", "vp": 2175, "price_dh": 108.75, "price_usd": 10.88, "image": "blackthorn_marshal.png"},
                {"name": "BLACKTHORN CLASSIC", "vp": 2175, "price_dh": 108.75, "price_usd": 10.88, "image": "blackthorn_classic.png"},
                {"name": "BLACKTHORN GUARDIAN", "vp": 2175, "price_dh": 108.75, "price_usd": 10.88, "image": "blackthorn_guardian.png"},
                {"name": "VCT X NS", "vp": 2320, "price_dh": 116.0, "price_usd": 11.60, "image": "vct_ns.png"}
            ]
            
            bot_dir = os.path.dirname(os.path.abspath(__file__))
            
            for bundle in bundles:
                bundle_embed = discord.Embed(
                    title=f"🎁 {bundle['name']} ({bundle['vp']:,} VP)",
                    description=f"**Price:** {bundle['price_usd']} $ | {bundle['price_dh']} DH",
                    color=0x2ECC71
                )
                
                image_path = os.path.join(bot_dir, bundle["image"])
                file = None
                
                if os.path.exists(image_path):
                    file = discord.File(image_path, filename=bundle["image"])
                    bundle_embed.set_image(url=f"attachment://{bundle['image']}")
                
                view = GiftingButtonView(bundle["name"], bundle["vp"], bundle["price_dh"], bundle["price_usd"])
                # Update label directly on the instance's first child (which is the button)
                view.children[0].label = f"🛒 Order {bundle['name']} - {bundle['price_dh']} DH"
                
                if file:
                    await interaction.channel.send(embed=bundle_embed, file=file, view=view)
                else:
                    await interaction.channel.send(embed=bundle_embed, view=view)
                    
            await interaction.channel.send(f"{interaction.user.mention} Please select your Discord Gifting Package from the options above!")
            
        else:
            # "Other" - No Modal, just prompt user to speak in chat
            try:
                # Move to Support Category
                guild = interaction.guild
                category = discord.utils.get(guild.categories, name="Support Tickets")
                if not category:
                    overwrites = {
                        guild.default_role: discord.PermissionOverwrite(view_channel=False)
                    }
                    category = await guild.create_category("Support Tickets", overwrites=overwrites)
                
                await interaction.channel.edit(category=category)
            except:
                pass
            
            embed = discord.Embed(
                title="❓ **Other / Support**",
                description="Please describe your Request / Issue directly in this chat.\nSupport will be with you shortly!",
                color=0x95A5A6
            )
            
            # Enable writing for user
            try:
                await interaction.channel.set_permissions(interaction.user, view_channel=True, send_messages=True, read_message_history=True)
            except Exception as e:
                print(f"Error setting permissions for Other: {e}")

            await interaction.response.send_message(embed=embed)

class ServiceView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ServiceSelect())

    @discord.ui.button(label="🔒 Close Ticket", style=discord.ButtonStyle.red, custom_id="close_ticket_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Are you sure you would like to close this ticket?", view=TicketCloseConfirmationView(), ephemeral=False)

async def auto_close_empty_ticket(channel: discord.TextChannel, user: discord.Member, delay_seconds: int = 600):
    """Wait for a specified time, if the user hasn't sent any message in the channel, delete it."""
    await asyncio.sleep(delay_seconds)
    
    try:
        current_channel = channel.guild.get_channel(channel.id)
        if current_channel is None:
            return # Channel already deleted
            
        # Verify if user has sent any message (excluding interactions/bots)
        # We check the last 50 messages to be safe.
        messages = [msg async for msg in current_channel.history(limit=50)]
        user_messaged = any(msg.author.id == user.id and msg.content.strip() != "" for msg in messages)
        
        if not user_messaged:
            # Delete completely, even if it was moved to orders or logs
            await current_channel.delete(reason="Auto-closed empty ticket due to inactivity.")
            try:
                await user.send(
                    f"⏰ **تم إغلاق التذكرة الخاصة بك في {channel.guild.name} تلقائياً.**\n"
                    f"السبب: لم تقم بكتابة أي رسالة داخل التذكرة لمدة 10 دقائق.\n\n"
                    f"*(Your ticket was automatically deleted due to 10 minutes of inactivity.)*"
                )
            except:
                pass
    except Exception as e:
        print(f"Error auto-closing empty ticket: {e}")

class TicketSystemView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📩 Open Ticket", style=discord.ButtonStyle.green, custom_id="create_ticket_btn")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="Tickets")
        
        if not category:
            category = await guild.create_category("Tickets")
            
        # Check if user already has a ticket in any relevant category (Active)
        ticket_categories = ["Tickets", "Orders", "Gifting Orders", "Valorant Points", "Support Tickets"]
        
        for cat_name in ticket_categories:
            cat = discord.utils.get(guild.categories, name=cat_name)
            if cat:
                for channel in cat.text_channels:
                    if interaction.user in channel.overwrites:
                        if channel.overwrites[interaction.user].view_channel:
                             await interaction.followup.send(f"❌ You already have an open ticket/order: {channel.mention}\n(Ma te9derch thoul ktar mn ticket wa7da f nefss lw9t.)", ephemeral=True)
                             return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=False, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        }

        channel = await guild.create_text_channel(f"ticket-{interaction.user.name}", category=category, overwrites=overwrites)
        
        embed = discord.Embed(
            title=f"👋 Welcome {interaction.user.name}!",
            description=(
                "### ⚠️ Action Required / مطلوب إجراء\n"
                "**Please select the service you want from the menu below to proceed.**\n"
                "**3afak khtar service li bghiti mn la liste lte7t bach nkml m3ak.** 👇"
            ),
            color=0x2ECC71
        )
        embed.add_field(
            name="⏱️ تنبيه / Warning",
            value="**انتباه:** سيتم إغلاق هذه التذكرة تلقائياً بعد 10 دقائق إذا لم تقم بكتابة أي رسالة.\n*(This ticket will auto-close in 10 minutes if you don't type any message.)*",
            inline=False
        )
        
        # Send ServiceView which has the Dropdown AND Close button
        await channel.send(f"{interaction.user.mention}", embed=embed, view=ServiceView())
        
        await interaction.followup.send(f"✅ Ticket created: {channel.mention}", ephemeral=True)
        
        # Start the auto-close timer (600 seconds = 10 minutes)
        bot.loop.create_task(auto_close_empty_ticket(channel, interaction.user, 600))

# Flag to ensure on_ready logic only runs once
bot_setup_done = False

@bot.event
async def on_ready():
    global bot_setup_done
    if bot_setup_done:
        print("Bot reconnected - skipping setup.")
        return
    print(f'Logged in as {bot.user.name}')
    print(f'Bot is ready! Instance ID: {INSTANCE_ID}')
    
    # Set Status
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Karys Shop | !help_shop"))
    
    # Register Persistent Views
    bot.add_view(TicketSystemView())
    # bot.add_view(TicketControlView()) # Removed/Replaced by ServiceView
    bot.add_view(ServiceView())
    bot.add_view(TicketAdminView())
    bot.add_view(TicketCloseConfirmationView())
    

    
    # Reload active giveaways
    for giveaway_id, data in giveaways_data.items():
        if not data["ended"]:
            bot.add_view(GiveawayJoinButton(giveaway_id, data["required_invites"]))
            
            # Resume timer
            try:
                end_time_ts = data.get("end_time")
                if end_time_ts:
                    now_ts = datetime.now().timestamp()
                    remaining = end_time_ts - now_ts
                    
                    if remaining <= 0:
                        # Ended while offline
                        bot.loop.create_task(end_giveaway_logic(giveaway_id))
                    else:
                        # Resume timer
                        bot.loop.create_task(schedule_giveaway_end(giveaway_id, remaining))
            except Exception as e:
                print(f"Error resuming giveaway {giveaway_id}: {e}")
            
    # Initialize invite cache - DISABLED TO PREVENT CLOUDFLARE 1015 ERROR
    # for guild in bot.guilds:
    #     try:
    #         invite_cache[guild.id] = await guild.invites()
    #         await asyncio.sleep(2) # Increased safety delay
    #     except Exception as e:
    #         print(f"Failed to fetch invites: {e}")
            
    bot_setup_done = True
    
    # Force Sync on Ready
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s) globally.")
    except Exception as e:
        print(f"Error syncing commands: {e}")
    # print("ℹ️ Note: Auto-sync is disabled to prevent crashes. Use '!sync' if you added new commands.")

@bot.command(name='prices', aliases=['p', 'price', 'prix', 'cost'])
async def prices(ctx):
    """Display price list"""
    try:
        embed = discord.Embed(
            title="🔻 Valorant Points Price List 🔻",
            color=0xFF0000  # Red color
        )
        
        # Add platform availability
        embed.add_field(
            name="🎮 Available on:",
            value="PlayStation 5 | Xbox | PC",
            inline=False
        )
        
        # Add prices
        price_text = ""
        for points, info in PRICE_LIST.items():
            # Using specific logic to match user request while keeping stock status
            # User template: 5,350 :vp: → 25 $ │ 249 dh
            points_int = int(points)
            if not info["stock"]:
                # Strikethrough for out of stock or just mark with X
                price_text += f"{points_int:,} <:vp:1466944483504427008> → {info['usd']} $ │ {info['dh']} dh (Out of Stock)\n"
            else:
                price_text += f"{points_int:,} <:vp:1466944483504427008> → {info['usd']} $ │ {info['dh']} dh\n"
        
        embed.add_field(
            name="💰 Prices",
            value=price_text,
            inline=False
        )
        
        # Add delivery info
        embed.add_field(
            name="🚚 Delivery:",
            value="⏱️ 1–5 minutes after payment confirmation",
            inline=False
        )
        
        # Add payment methods
        embed.add_field(
            name="💳 Payment Methods:",
            value="• 🏦 Bank transfer: CIH Bank | BMCE Bank | Attijariwafa Bank\n• ⚡ Instant bank transfer\n• 🪙 Binance (USDT)\n• 💲 PayPal",
            inline=False
        )
        
        # Add order instructions
        embed.add_field(
            name="📩 Order:",
            value="Send payment proof in the payment ticket channel",
            inline=False
        )
        
        # Set footer
        embed.set_footer(text="Karys Shop | Trusted Valorant Points Provider")

        
        view = TicketButton(ctx.guild.id)
        # Use karys.png for prices command as well (consistent branding)
        # Use karys.png from current directory
        bot_dir = os.path.dirname(os.path.abspath(__file__))
        image_path = os.path.join(bot_dir, "karys.png")
             
        if os.path.exists(image_path):
            file = discord.File(image_path, filename="karys.png")
            embed.set_image(url="attachment://karys.png")
            await ctx.send(embed=embed, file=file, view=view)
        else:
            await ctx.send(embed=embed, view=view)
        print(f'[PRICES] Embed sent successfully')
    except Exception as e:
        print(f'[ERROR] Error in prices command: {e}')
        import traceback
        traceback.print_exc()
        await ctx.send(f'❌ Error: {str(e)}')

@bot.command(name='stock', aliases=['inventory'])
async def stock(ctx):
    """Check stock availability"""
    
    embed = discord.Embed(
        title="📦 Stock Status",
        color=0x00FF00
    )
    
    in_stock = []
    out_of_stock = []
    
    for points, info in PRICE_LIST.items():
        points_int = int(points)
        if info["stock"]:
            in_stock.append(f"{points_int:,} VP")
        else:
            out_of_stock.append(f"{points_int:,} VP")
    
    if in_stock:
        embed.add_field(
            name="✅ In Stock:",
            value="\n".join(in_stock),
            inline=True
        )
    
    if out_of_stock:
        embed.add_field(
            name="❌ Out of Stock:",
            value="\n".join(out_of_stock),
            inline=True
        )
    
    await ctx.send(embed=embed)

@bot.command(name='order')
async def order(ctx, points: str = None):
    """Order Valorant Points"""
    if not points:
        await ctx.send("❌ Please specify the amount of Valorant Points you want to order.\nExample: `!order 10000`")
        return
    
    # Remove commas if user added them
    points = points.replace(",", "")
    
    if points not in PRICE_LIST:
        await ctx.send(f"❌ Invalid amount. Use `!prices` to see available options.")
        return
    
    info = PRICE_LIST[points]
    
    if not info["stock"]:
        points_int = int(points)
        await ctx.send(f"❌ {points_int:,} VP is currently out of stock.")
        return
    
    embed = discord.Embed(
        title="🛒 Order Confirmation",
        color=0x00FF00
    )
    
    points_int = int(points)
    embed.add_field(
        name="Amount:",
        value=f"{points_int:,} Valorant Points",
        inline=False
    )
    
    embed.add_field(
        name="Price:",
        value=f"{info['usd']} $ | {info['dh']} dh",
        inline=False
    )
    
    embed.add_field(
        name="Next Steps:",
        value="1. Make payment using one of the accepted methods\n2. Send payment proof in a ticket\n3. Receive your VP within 1-5 minutes",
        inline=False
    )
    
    embed.add_field(
        name="Payment Methods:",
        value="Bank transfer (CIH/BMCE/Attijari) / Binance (USDT) / PayPal",
        inline=False
    )
    
    view = TicketButton(ctx.guild.id)
    await ctx.send(embed=embed, view=view)

@bot.command(name="help_shop")
async def help_shop(ctx):
    embed = discord.Embed(
        title="🛍️ Karys Shop - Commands",
        description="Here are the available commands:",
        color=0x2f3136
    )
    
    # Prefix Commands
    embed.add_field(name="!prices", value="View Valorant Points price list", inline=False)
    embed.add_field(name="!stock", value="Check stock availability", inline=False)
    embed.add_field(name="!order [amount]", value="Order Valorant Points (e.g., !order 10000)", inline=False)
    embed.add_field(name="!rules", value="Display buying terms and rules", inline=False)
    embed.add_field(name="!spotify", value="Display Spotify Premium subscription plans", inline=False)
    embed.add_field(name="!nitro", value="Display Discord Nitro Premium plans", inline=False)
    embed.add_field(name="!boost", value="Display Server Boost prices", inline=False)
    embed.add_field(name="!gift", value="Display Valorant Gifting Service", inline=False)
    embed.add_field(name="!help_shop", value="Show this help message", inline=False)
    
    # Slash Commands
    embed.add_field(name="──────────────", value="**Slash Commands (Recommended):**", inline=False)
    embed.add_field(name="/kgiveaway", value="Create and Manage Giveaways (Admin)", inline=False)
    embed.add_field(name="/vbucks", value="View Fortnite V-Bucks prices", inline=False)
    embed.add_field(name="/ticket_panel", value="Deploy Ticket System (Admin)", inline=False)
    
    embed.set_footer(text="Karys Shop | Your trusted Valorant Points provider")
    await ctx.send(embed=embed)

@bot.command(name='rules', aliases=['terms'])
async def rules(ctx):
    """Display buying terms and rules"""
    embed = discord.Embed(
        title="📜 RULES — BUYING TERMS",
        color=0xFF0000
    )
    
    # Security & Trust
    embed.add_field(
        name="🔐 Security & Trust",
        value="🛡️ Purchases must be made only through verified admins or sellers.\n👤 Anyone claiming to be staff without official confirmation should be ignored.",
        inline=False
    )
    
    # Order Processing
    embed.add_field(
        name="⏱️ Order Processing",
        value="⚡ Orders are delivered within 1 to 5 minutes after payment confirmation.",
        inline=False
    )
    
    # Refund Policy
    embed.add_field(
        name="💸 Refund Policy",
        value="❌ No refunds will be issued once the product has been successfully delivered.",
        inline=False
    )
    
    # Liability
    embed.add_field(
        name="🚫 Liability",
        value="📩 The server is not responsible for scams via private messages or fake accounts.\n🔎 Always verify the official Discord tag before sending payment.",
        inline=False
    )
    
    # Important Warning
    embed.add_field(
        name="🚨 Important Warning",
        value="🎁 Do not trust fake discounts, giveaways, or edited screenshots.",
        inline=False
    )
    
    # Secure Payments
    embed.add_field(
        name="🏦 Secure Payments",
        value="✅ Payments must be made only through official payment channels or verified shop contacts.",
        inline=False
    )
    
    embed.set_footer(text="Karys Shop")
    
    await ctx.send(embed=embed)

@bot.command(name='spotify', aliases=['spotify_plans', 'سبوتيفاي'])
async def spotify(ctx):
    """Display Spotify subscription plans"""
    embed = discord.Embed(
        title="🎵 Spotify Premium | Karys Shop",
        description="**Unleash the power of music!** 🎧\nAd-free music listening, offline playback, and more.",
        color=0x1DB954
    )
    
    # Individual Plan
    embed.add_field(
        name="👤 Individual Plan",
        value="> *Your own personal premium account*\n```ini\n[ 6 Months  ]  $30  (was $59.99)\n[ 12 Months ]  $40  (was $99.99)\n```",
        inline=False
    )
    
    # Duo Plan
    embed.add_field(
        name="👥 Duo Plan (2 Accounts)",
        value="> *Perfect for couples or besties*\n```ini\n[ 6 Months  ]  $40  (was $89.99)\n[ 12 Months ]  $55  (was $179.99)\n```",
        inline=False
    )
    
    # Features
    embed.add_field(
        name="✨ Why Choose Premium?",
        value="✅ *Full Warranty coverage*\n✅ *Works on your existing account*\n✅ *No VPN needed*\n❌ *Account must be free (no active sub)*",
        inline=False
    )
    
    # Ready to buy
    embed.add_field(
        name="💳 Ready to Upgrade?",
        value="Click the **Open a Ticket** button below or go to <#1485141935210365171>! 📩",
        inline=False
    )
    
    embed.set_footer(text="Karys Shop • 100% Satisfaction 💚")
    
    # Add Spotify image from local file (current directory)
    bot_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(bot_dir, "spotify.png")
    
    if os.path.exists(image_path):
        try:
            file = discord.File(image_path, filename="spotify.png")
            embed.set_image(url=f"attachment://spotify.png")
            view = TicketButton(ctx.guild.id)
            await ctx.send(embed=embed, file=file, view=view)
        except Exception as e:
            print(f"[ERROR] Failed to send Spotify image: {e}")
            view = TicketButton(ctx.guild.id)
            await ctx.send(embed=embed, view=view)
    else:
        # Fallback
        embed.set_image(url="https://upload.wikimedia.org/wikipedia/commons/thumb/1/19/Spotify_logo_without_text.svg/1200px-Spotify_logo_without_text.svg.png")
        view = TicketButton(ctx.guild.id)
        await ctx.send(embed=embed, view=view)

@bot.command(name='nitro', aliases=['discord_nitro', 'نترو'])
async def nitro(ctx):
    """Display Discord Nitro Premium plans"""
    embed = discord.Embed(
        title="✨ Discord Nitro Premium | Karys Shop",
        description="**Upgrade your Discord experience with premium perks!** 🚀\nChoose the plan that suits you best below.",
        color=0x5865F2
    )

    # Gift Plan
    embed.add_field(
        name="🎁 Nitro Premium (Gift)",
        value="> *Safe, Stackable, Instant Delivery*\n```ini\n[ 1 Month ]  $8   (was $9.99)\n[ 1 Year  ]  $90  (was $99.99)\n```",
        inline=False
    )
    
    # No Login Plan
    embed.add_field(
        name="🛡️ Nitro Premium (No Login)",
        value="> *No password needed, 100% Safe*\n```ini\n[ 1 Year  ]  $60  (was $99.99)\n```\n❌ *Must have no active subscription*",
        inline=False
    )
    
    # Login Plan
    embed.add_field(
        name="⚡ Nitro Premium (Login)",
        value="> *Cheapest Option, Login Required*\n```ini\n[ 1 Year  ]  $50  (was $99.99)\n```\n❌ *Must have no active subscription*",
        inline=False
    )
    
    # Check current day/time availability or random footer
    embed.add_field(
        name="💳 Ready to buy?",
        value="Click the **Open a Ticket** button below or go to <#1485141935210365171>! 📩",
        inline=False
    )
    
    embed.set_footer(text="Karys Shop • Trusted Service 💎")
    
    # Image handling logic (nitro.png in current dir)
    bot_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(bot_dir, "nitro.png")
    
    view = TicketButton(ctx.guild.id)
    
    if os.path.exists(image_path):
        try:
            file = discord.File(image_path, filename="nitro.png")
            embed.set_image(url=f"attachment://nitro.png")
            await ctx.send(embed=embed, file=file, view=view)
        except Exception as e:
            print(f"[ERROR] Failed to send Nitro image: {e}")
            await ctx.send(embed=embed, view=view)
    else:
        # Fallback
        embed.set_image(url="https://cdn.discordapp.com/attachments/1061648397301522472/1061648397301522473/nitro-banner.png")
        await ctx.send(embed=embed, view=view)

@bot.command(name='boost', aliases=['boosts', 'server_boost', 'بوست'])
async def boost(ctx):
    """Display Server Boost prices"""
    embed = discord.Embed(
        title="🚀 Server Boosts | Karys Shop",
        description="**Level up your community!** 💎\nPremium boosts with 3 months warranty.",
        color=0xF47FFF
    )
    
    # 6x Boosts
    embed.add_field(
        name="<:boost_icon:1335969248479707136> 6x Server Boosts",
        value="○ 3 Months\n╰ $8",
        inline=False
    )

    # 8x Boosts
    embed.add_field(
        name="<:boost_icon:1335969248479707136> 8x Server Boosts (Level 2)",
        value="○ 3 Months\n╰ $10",
        inline=False
    )
    
    # 14x Boosts
    embed.add_field(
        name="<:boost_icon:1335969248479707136> 14x Server Boosts (Level 3)",
        value="○ 3 Months\n╰ $20",
        inline=False
    )

    # 20x Boosts
    embed.add_field(
        name="<:boost_icon:1335969248479707136> 20x Server Boosts",
        value="○ 3 Months\n╰ $25",
        inline=False
    )

    # 26x Boosts
    embed.add_field(
        name="<:boost_icon:1335969248479707136> 26x Server Boosts",
        value="○ 3 Months\n╰ $30",
        inline=False
    )

    # 30x Boosts
    embed.add_field(
        name="🔥 30x Server Boosts",
        value="○ 3 Months\n╰ $35",
        inline=False
    )
    
    # Ready to buy
    embed.add_field(
        name="💳 Ready to Boost?",
        value="Click the **Open a Ticket** button below or go to <#1485141935210365171>! 📩",
        inline=False
    )
    
    embed.set_footer(text="Karys Shop • High Quality Boosts 💎")
    
    # Image handling logic (boost.png in current dir)
    bot_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(bot_dir, "boost.png")
    
    view = TicketButton(ctx.guild.id)
    
    if os.path.exists(image_path):
        try:
            file = discord.File(image_path, filename="boost.png")
            embed.set_image(url=f"attachment://boost.png")
            await ctx.send(embed=embed, file=file, view=view)
        except Exception as e:
            print(f"[ERROR] Failed to send Boost image: {e}")
            await ctx.send(embed=embed, view=view)
    else:
        # Fallback image
        embed.set_image(url="https://support.discord.com/hc/article_attachments/360013500334/Nitro_Server_Boost_101.jpg")
        await ctx.send(embed=embed, view=view)

@bot.command(name='gift', aliases=['gifting', 'الهدايا', 'هدايا'])
async def gift(ctx):
    """Display Gifting Announcement"""
    embed = discord.Embed(
        title="🎁 OFFICIAL GIFTING SERVICE",
        description="**Get your favorite Valorant skins & bundles directly in-game!**\nWe offer a safe and instant gifting service.",
        color=0xFD4556  # Valorant Red
    )
    
    # Riot ID Section with clear formatting
    embed.add_field(
        name="🆔 Riot IDs to Add (Select your region)",
        value=(
            "**🇪🇺 Europe:** `DALAS L7#9999`\n"
            "**🇹🇷 Turkey:** `DALAS L7#BOSS`\n\n"
            "*Send a friend request to the correct account to start.*"
        ),
        inline=False
    )
    
    # English Process
    embed.add_field(
        name="🇺🇸 How it works",
        value=(
            "**1️⃣ Add Friend:** Send a request to the ID above.\n"
            "**2️⃣ Wait 7 Days:** Wait the mandatory 7-day period (Riot Rule).\n" # Corrected to 24h as standard validation, though user said 7 days? standard is 24h for gifting usually, but user said 7 days "mandatory". I should STICK TO USER TEXT calling it 7 days.
            "**3️⃣ Payment:** Pay via CIH / Attijari / Crypto.\n"
            "**4️⃣ Receive:** Get your skin/bundle instantly!"
        ),
        inline=False
    )
    
    embed.add_field(name=" ", value="━━━━━━━━━━━━━━━━━━━━━━", inline=False) # Separator

    # Arabic Process
    embed.add_field(
        name="🇲🇦 طريقة العمل",
        value=(
            "**1️⃣ طلب صداقة:** أرسل طلب للآيدي الموضح أعلاه.\n"
            "**2️⃣ الانتظار:** انتظر مدة 7 أيام (قانون اللعبة).\n" # Stick to user's "7 days"
            "**3️⃣ الدفع:** ادفع عبر CIH / التجاري / Crypto.\n"
            "**4️⃣ الاستلام:** استلم هديتك فوراً!"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🛡️ 100% Safe & Secure",
        value="Click the **Open a Ticket** button below to order! 📩",
        inline=False
    )

    embed.set_footer(text="Karys Shop | Valorant Gifting Service", icon_url=bot.user.avatar.url if bot.user.avatar else None)
    
    # Try to add a thumbnail if Karys logo exists (karys.png in current dir)
    bot_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(bot_dir, "karys.png")
         
    view = TicketButton(ctx.guild.id)

    if os.path.exists(image_path):
        file = discord.File(image_path, filename="karys.png")
        embed.set_thumbnail(url="attachment://karys.png")
        await ctx.send(embed=embed, file=file, view=view)
    else:
        await ctx.send(embed=embed, view=view)

@bot.tree.command(name="gift", description="Display Gifting Announcement")
async def gift_slash(interaction: discord.Interaction):
    """Slash command to display Gifting Announcement"""
    embed = discord.Embed(
        title="🎁 OFFICIAL GIFTING SERVICE",
        description="**Get your favorite Valorant skins & bundles directly in-game!**\nWe offer a safe and instant gifting service.",
        color=0xFD4556  # Valorant Red
    )
    
    # Riot ID with code block
    embed.add_field(
        name="🆔 Riot IDs to Add (Select your region)",
        value=(
            "**🇪🇺 Europe:** `DALAS L7#9999`\n"
            "**🇹🇷 Turkey:** `DALAS L7#BOSS`\n\n"
            "*Send a friend request to the correct account to start.*"
        ),
        inline=False
    )
    
    # How it works
    embed.add_field(
        name="✨ How it works",
        value=(
            "**1️⃣ Add Friend:** Send a request to the ID above.\n"
            "**2️⃣ Wait 7 Days:** Wait the mandatory 7-day period (Riot Rule).\n"
            "**3️⃣ Payment:** Pay via Credit Card / Crypto / PayPal.\n"
            "**4️⃣ Receive:** Get your skin/bundle instantly!"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🛡️ 100% Safe & Secure",
        value="Click the **Order Ticket** button below to order! 📩",
        inline=False
    )

    embed.set_footer(text="Karys Shop | Valorant Gifting Service", icon_url=interaction.client.user.avatar.url if interaction.client.user.avatar else None)
    
    # Image logic for slash command (karys.png in current dir)
    bot_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(bot_dir, "karys.png")
    
    view = TicketButton(interaction.guild_id)
    
    if os.path.exists(image_path):
        file = discord.File(image_path, filename="karys.png")
        embed.set_thumbnail(url="attachment://karys.png")
        await interaction.response.send_message(embed=embed, file=file, view=view)
    else:
        await interaction.response.send_message(embed=embed, view=view)


@bot.tree.command(name="spotify", description="عرض خطط Spotify Premium")
async def spotify_slash(interaction: discord.Interaction):
    """Slash command to display Spotify plans"""
    embed = discord.Embed(
        title="🎵 Spotify Premium | Karys Shop",
        description="**Unleash the power of music!** 🎧\nAd-free music listening, offline playback, and more.",
        color=0x1DB954
    )
    
    # Individual Plan
    embed.add_field(
        name="👤 Individual Plan",
        value="> *Your own personal premium account*\n```ini\n[ 6 Months  ]  $30  (was $59.99)\n[ 12 Months ]  $40  (was $99.99)\n```",
        inline=False
    )
    
    # Duo Plan
    embed.add_field(
        name="👥 Duo Plan (2 Accounts)",
        value="> *Perfect for couples or besties*\n```ini\n[ 6 Months  ]  $40  (was $89.99)\n[ 12 Months ]  $55  (was $179.99)\n```",
        inline=False
    )
    
    # Features
    embed.add_field(
        name="✨ Why Choose Premium?",
        value="✅ *Full Warranty coverage*\n✅ *Works on your existing account*\n✅ *No VPN needed*\n❌ *Account must be free (no active sub)*",
        inline=False
    )
    
    # Ready to buy
    embed.add_field(
        name="💳 Ready to Upgrade?",
        value="Click the **Order Ticket** below or contact an admin! 📩",
        inline=False
    )
    
    embed.set_footer(text="Karys Shop • 100% Satisfaction 💚")
    
    # Image handling logic (spotify.png in current dir)
    bot_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(bot_dir, "spotify.png")
    
    if os.path.exists(image_path):
        try:
            file = discord.File(image_path, filename="spotify.png")
            embed.set_image(url=f"attachment://spotify.png")
            view = TicketButton(interaction.guild_id)
            await interaction.response.send_message(embed=embed, file=file, view=view)
        except Exception as e:
            print(f"[ERROR] Failed to send Spotify image: {e}")
            view = TicketButton(interaction.guild_id)
            await interaction.response.send_message(embed=embed, view=view)
    else:
        # Fallback
        embed.set_image(url="https://upload.wikimedia.org/wikipedia/commons/thumb/1/19/Spotify_logo_without_text.svg/1200px-Spotify_logo_without_text.svg.png")
        view = TicketButton(interaction.guild_id)
        await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="nitro", description="عرض خطط Discord Nitro Premium")
async def nitro_slash(interaction: discord.Interaction):
    """Slash command to display Nitro plans"""
    embed = discord.Embed(
        title="✨ Discord Nitro Premium | Karys Shop",
        description="**Upgrade your Discord experience with premium perks!** 🚀\nChoose the plan that suits you best below.",
        color=0x5865F2
    )

    # Gift Plan
    embed.add_field(
        name="🎁 Nitro Premium (Gift)",
        value="> *Safe, Stackable, Instant Delivery*\n```ini\n[ 1 Month ]  $8   (was $9.99)\n[ 1 Year  ]  $90  (was $99.99)\n```",
        inline=False
    )
    
    # No Login Plan
    embed.add_field(
        name="🛡️ Nitro Premium (No Login)",
        value="> *No password needed, 100% Safe*\n```ini\n[ 1 Year  ]  $60  (was $99.99)\n```\n❌ *Must have no active subscription*",
        inline=False
    )
    
    # Login Plan
    embed.add_field(
        name="⚡ Nitro Premium (Login)",
        value="> *Cheapest Option, Login Required*\n```ini\n[ 1 Year  ]  $50  (was $99.99)\n```\n❌ *Must have no active subscription*",
        inline=False
    )
    
    # Check current day/time availability or random footer
    embed.add_field(
        name="💳 Ready to buy?",
        value="Click the **Open a Ticket** button below or go to <#1485141935210365171>! 📩",
        inline=False
    )
    
    embed.set_footer(text="Karys Shop • Trusted Service 💎")
    
    # Image handling logic (nitro.png in current dir)
    bot_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(bot_dir, "nitro.png")
    
    view = TicketButton(interaction.guild_id)
    
    if os.path.exists(image_path):
        try:
            file = discord.File(image_path, filename="nitro.png")
            embed.set_image(url=f"attachment://nitro.png")
            await interaction.response.send_message(embed=embed, file=file, view=view)
        except Exception as e:
            print(f"[ERROR] Failed to send Nitro image: {e}")
            await interaction.response.send_message(embed=embed, view=view)
    else:
        # Fallback
        embed.set_image(url="https://cdn.discordapp.com/attachments/1061648397301522472/1061648397301522473/nitro-banner.png")
        await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="boost", description="عرض أسعار Server Boosts")
async def boost_slash(interaction: discord.Interaction):
    """Slash command to display Boost prices"""
    embed = discord.Embed(
        title="🚀 Server Boosts | Karys Shop",
        description="**Level up your community!** 💎\nPremium boosts with 3 months warranty.",
        color=0xF47FFF
    )
    
    # 6x Boosts
    embed.add_field(
        name="<:boost_icon:1335969248479707136> 6x Server Boosts",
        value="○ 3 Months\n╰ $8",
        inline=False
    )

    # 8x Boosts
    embed.add_field(
        name="<:boost_icon:1335969248479707136> 8x Server Boosts (Level 2)",
        value="○ 3 Months\n╰ $10",
        inline=False
    )
    
    # 14x Boosts
    embed.add_field(
        name="<:boost_icon:1335969248479707136> 14x Server Boosts (Level 3)",
        value="○ 3 Months\n╰ $20",
        inline=False
    )

    # 20x Boosts
    embed.add_field(
        name="<:boost_icon:1335969248479707136> 20x Server Boosts",
        value="○ 3 Months\n╰ $25",
        inline=False
    )

    # 26x Boosts
    embed.add_field(
        name="<:boost_icon:1335969248479707136> 26x Server Boosts",
        value="○ 3 Months\n╰ $30",
        inline=False
    )

    # 30x Boosts
    embed.add_field(
        name="🔥 30x Server Boosts",
        value="○ 3 Months\n╰ $35",
        inline=False
    )
    
    # Ready to buy
    embed.add_field(
        name="💳 Ready to Boost?",
        value="Click the **Open a Ticket** button below or go to <#1485141935210365171>! 📩",
        inline=False
    )
    
    embed.set_footer(text="Karys Shop • High Quality Boosts 💎")
    
    # Image handling logic (boost.png in current dir)
    bot_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(bot_dir, "boost.png")
    
    view = TicketButton(interaction.guild_id)
    
    if os.path.exists(image_path):
        try:
            file = discord.File(image_path, filename="boost.png")
            embed.set_image(url=f"attachment://boost.png")
            await interaction.response.send_message(embed=embed, file=file, view=view)
        except Exception as e:
            print(f"[ERROR] Failed to send Boost image: {e}")
            await interaction.response.send_message(embed=embed, view=view)
    else:
        # Fallback image
        embed.set_image(url="https://support.discord.com/hc/article_attachments/360013500334/Nitro_Server_Boost_101.jpg")
        await interaction.response.send_message(embed=embed, view=view)

def create_price_post():
    """Create price list post matching exact format"""
    # Create embed with exact format
    embed = discord.Embed(
        title="🔻 Valorant Points Price List 🔻",
        color=0xFF0000  # Red color
    )
    
    # Add platform availability
    embed.add_field(
        name="🎮 Available on:",
        value="PlayStation 5 | Xbox | PC",
        inline=False
    )
    
    # Add prices - matching exact format
    price_text = ""
    for points, info in PRICE_LIST.items():
        points_int = int(points)
        # Use :vp: custom emoji with ID
        price_text += f"{points_int:,} <:vp:1466944483504427008> → {info['usd']} $ │ {info['dh']} dh\n"
    
    embed.add_field(
        name="💰 Prices",
        value=price_text,
        inline=False
    )
    
    # Add delivery info
    embed.add_field(
        name="🚚 Delivery:",
        value="⏱️ 1–5 minutes after payment confirmation",
        inline=False
    )
    
    # Add payment methods
    embed.add_field(
        name="💳 Payment Methods:",
        value="• 🏦 Bank transfer: CIH Bank | BMCE Bank | Attijariwafa Bank\n• ⚡ Instant bank transfer\n• 🪙 Binance (USDT)\n• 💲 PayPal",
        inline=False
    )
    
    # Add order instructions
    embed.add_field(
        name="📩 Order:",
        value="Send payment proof in the payment <#1485141935210365171> .",
        inline=False
    )
    
    # Set footer
    embed.set_footer(text="Karys Shop")
    
    return embed

@bot.tree.command(name="post", description="إنشاء منشور قائمة الأسعار")
async def post(interaction: discord.Interaction):
    """Slash command to post price list"""
    embed = create_price_post()
    # Add KARYS SHOP promotional image from local file (karys.png in current dir)
    # Get the directory where bot.py is located
    bot_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(bot_dir, "karys.png")
    
    if os.path.exists(image_path):
        print(f"[INFO] Found image at: {image_path}")
        try:
            # Create Discord File object directly from file path
            file = discord.File(image_path, filename="karys.png")
            embed.set_image(url=f"attachment://karys.png")
            view = TicketButton(interaction.guild_id)
            await interaction.response.send_message(embed=embed, file=file, view=view)
            print(f"[SUCCESS] Image sent successfully")
        except Exception as e:
            print(f"[ERROR] Failed to send image: {e}")
            # Try sending without image
            view = TicketButton(interaction.guild_id)
            await interaction.response.send_message(embed=embed, view=view)
    else:
        print(f"[WARNING] Image not found at: {image_path}")
        view = TicketButton(interaction.guild_id)
        await interaction.response.send_message(embed=embed, view=view)

@bot.command(name='post', aliases=['منشور'])
async def post_command(ctx):
    """Create price list post"""
    embed = create_price_post()
    # Add KARYS SHOP promotional image from local file (karys.png in current dir)
    # Get the directory where bot.py is located
    bot_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(bot_dir, "karys.png")
    
    view = TicketButton(ctx.guild.id)
    if os.path.exists(image_path):
        print(f"[INFO] Found image at: {image_path}")
        try:
            # Create Discord File object directly from file path
            file = discord.File(image_path, filename="karys.png")
            embed.set_image(url=f"attachment://karys.png")
            await ctx.send(embed=embed, file=file, view=view)
            print(f"[SUCCESS] Image sent successfully")
        except Exception as e:
            print(f"[ERROR] Failed to send image: {e}")
            # Try sending without image
            await ctx.send(embed=embed, view=view)
    else:
        print(f"[WARNING] Image not found at: {image_path}")
        await ctx.send(embed=embed, view=view)

@bot.command(name='payment', aliases=['pay', 'bank', 'rib', 'الدفع'])
async def payment(ctx):
    """Display Payment Methods"""
    embed = discord.Embed(
        title="💳 **SECURE PAYMENT METHODS** | طرق الدفع",
        description=(
            "To complete your purchase, please choose a payment method below and **open a ticket**.\n"
            "لإتمام عملية الشراء، اختر طريقة الدفع وافتح تذكرة."
        ),
        color=0xFF0000 
    )

    # Bank Transfer Section
    embed.add_field(
        name="🏦 **Bank Transfer** (تحويل بنكي)",
        value=(
            "> **CIH Bank**\n"
            "> **BMCE Bank**\n"
            "> **Attijariwafa Bank**\n"
            "> **Barid Bank**\n"
            "```fix\n"
            "Open a ticket to receive RIB / Account Number\n"
            "افتح تذكرة للحصول على رقم الحساب البنكي"
            "\n```"
        ),
        inline=False
    )
    
    # Crypto & Electronic Section
    embed.add_field(
        name="🪙 **Crypto & E-Wallets**",
        value=(
            "> **Binance Pay** (USDT)\n"
            "> **USDT (TRC20)**\n"
            "> **PayPal** (FnF Only)\n"
            "```fix\n"
            "Open a ticket to receive Wallet / Email\n"
            "افتح تذكرة للحصول على المحفظة أو البريد"
            "\n```"
        ),
        inline=False
    )

    # Separator
    embed.add_field(name=" ", value="━━━━━━━━━━━━━━━━━━━━━━", inline=False)
    
    # Process Steps
    embed.add_field(
        name="📝 **How to Order?** (كيفاش تشري؟)",
        value=(
            "1️⃣ **Open Ticket** 📩 : Click the button below.\n"
            "2️⃣ **Selection** 🗣️ : Tell us payment method + Product.\n"
            "3️⃣ **Payment** 💸 : Send the money & Screenshot.\n"
            "4️⃣ **Delivery** 🚀 : Receive your product instantly!"
        ),
        inline=False
    )
    
    embed.set_footer(text="Karys Shop | Trusted & Secure 🔒", icon_url=bot.user.avatar.url if bot.user.avatar else None)
    
    # Image handling logic (karys.png in current dir)
    bot_dir = os.path.dirname(os.path.abspath(__file__))
    karys_image_path = os.path.join(bot_dir, "karys.png")

    view = TicketButton(ctx.guild.id)
    
    if os.path.exists(karys_image_path):
        try:
            file = discord.File(karys_image_path, filename="karys.png")
            embed.set_thumbnail(url="attachment://karys.png")
            await ctx.send(embed=embed, file=file, view=view)
        except Exception as e:
            print(f"[ERROR] Failed to send image: {e}")
            await ctx.send(embed=embed, view=view)
    else:
        await ctx.send(embed=embed, view=view)

@bot.command(name='clean_logs')
@commands.has_permissions(administrator=True)
async def clean_logs(ctx):
    """Clean empty tickets from all Ticket Logs categories"""
    message = await ctx.send("⏳ Scanning all `Ticket Logs` categories for empty tickets...\n*This might take a minute to avoid Discord rate limits.*")
    deleted = 0
    
    # Check all Ticket Logs categories (up to 15)
    for i in range(16):
        cat_name = "Ticket Logs" if i == 0 else f"Ticket Logs{i}"
        category = discord.utils.get(ctx.guild.categories, name=cat_name)
        
        if category:
            for channel in category.text_channels:
                try:
                    # Check the last 50 messages in the channel
                    messages = [msg async for msg in channel.history(limit=50)]
                    # Check if any non-bot user sent a message containing text
                    user_messaged = any(not msg.author.bot and msg.content.strip() != "" for msg in messages)
                    
                    if not user_messaged:
                        await channel.delete(reason="Admin cleanup of empty tickets.")
                        deleted += 1
                        # Crucial wait to avoid discord API rate limits when deleting many channels
                        await asyncio.sleep(1.5)
                except discord.NotFound:
                    pass
                except Exception as e:
                    print(f"Error checking/deleting {channel.name}: {e}")
                    
    await message.edit(content=f"✅ **Cleanup complete!** Deleted **{deleted}** empty tickets from the logs.")



@bot.tree.command(name="payment", description="عرض طرق الدفع (Show Payment Methods)")
async def payment_slash(interaction: discord.Interaction):
    """Slash command to display Payment Methods"""
    embed = discord.Embed(
        title="💳 **SECURE PAYMENT METHODS** | طرق الدفع",
        description=(
            "To complete your purchase, please choose a payment method below and **open a ticket**.\n"
            "لإتمام عملية الشراء، اختر طريقة الدفع وافتح تذكرة."
        ),
        color=0xFF0000 
    )

    # Bank Transfer Section
    embed.add_field(
        name="🏦 **Bank Transfer** (تحويل بنكي)",
        value=(
            "> **CIH Bank**\n"
            "> **BMCE Bank**\n"
            "> **Attijariwafa Bank**\n"
            "> **Barid Bank**\n"
            "```fix\n"
            "Open a ticket to receive RIB / Account Number\n"
            "افتح تذكرة للحصول على رقم الحساب البنكي"
            "\n```"
        ),
        inline=False
    )
    
    # Crypto & Electronic Section
    embed.add_field(
        name="🪙 **Crypto & E-Wallets**",
        value=(
            "> **Binance Pay** (USDT)\n"
            "> **USDT (TRC20)**\n"
            "> **PayPal** (FnF Only)\n"
            "```fix\n"
            "Open a ticket to receive Wallet / Email\n"
            "افتح تذكرة للحصول على المحفظة أو البريد"
            "\n```"
        ),
        inline=False
    )

    # Separator
    embed.add_field(name=" ", value="━━━━━━━━━━━━━━━━━━━━━━", inline=False)
    
    # Process Steps
    embed.add_field(
        name="📝 **How to Order?** (كيفاش تشري؟)",
        value=(
            "1️⃣ **Open Ticket** 📩 : Click the button below.\n"
            "2️⃣ **Selection** 🗣️ : Tell us payment method + Product.\n"
            "3️⃣ **Payment** 💸 : Send the money & Screenshot.\n"
            "4️⃣ **Delivery** 🚀 : Receive your product instantly!"
        ),
        inline=False
    )
    
    embed.set_footer(text="Karys Shop | Trusted & Secure 🔒", icon_url=interaction.client.user.avatar.url if interaction.client.user.avatar else None)
    
    # Image handling logic
    bot_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(bot_dir)
    karys_image_path = os.path.join(parent_dir, "IMG", "karys.png")
    if not os.path.exists(karys_image_path):
         karys_image_path = os.path.join(bot_dir, "IMG", "karys.png")
    
    view = TicketButton(interaction.guild_id)
    
    if os.path.exists(karys_image_path):
        try:
            file = discord.File(karys_image_path, filename="karys.png")
            embed.set_thumbnail(url="attachment://karys.png")
            await interaction.response.send_message(embed=embed, file=file, view=view)
        except Exception as e:
            print(f"[ERROR] Failed to send image: {e}")
            await interaction.response.send_message(embed=embed, view=view)
    else:
        await interaction.response.send_message(embed=embed, view=view)

@bot.command(name='vbucks', aliases=['vb', 'fortnite', 'vbuck', 'فورتنايت'])
async def vbucks(ctx):
    """Display Fortnite V-Bucks Prices"""
    embed = discord.Embed(
        title="<:Vbucks:1470075477975630059> **FORTNITE V-BUCKS PRICES**",
        description="**Get your V-Bucks safely and instantly!** ⚡\n*Legal & Safe 100%*",
        color=0x9146FF # Purple Color
    )
    
    # Price List
    embed.add_field(
        name="💸 **Price List**",
        value=(
            "> **10,000 V-Bucks**  →  **400 DH**\n"
            "> **12,000 V-Bucks**  →  **480 DH**\n"
            "> **15,000 V-Bucks**  →  **600 DH**\n"
            "> **25,000 V-Bucks**  →  **1000 DH**\n"
            "> **50,000 V-Bucks**  →  **1800 DH**"
        ),
        inline=False
    )
    
    # Process
    embed.add_field(
        name="📝 **How to Buy?**",
        value=(
            "1️⃣ **Open Ticket** 📩 : Click button below\n"
            "2️⃣ **Payment** 💳 : <#1466153813323808849>\n"
            "3️⃣ **Delivery** 🚀 : Instant delivery to your account"
        ),
        inline=False
    )
    
    embed.set_footer(text="Karys Shop | Fortnite Services 🛒", icon_url=bot.user.avatar.url if bot.user.avatar else None)
    
    # Image handling logic
    bot_dir = os.path.dirname(os.path.abspath(__file__))
    
    # User requested specific image: image.png for vbucks
    image_path = os.path.join(bot_dir, "image.png")
    
    # Fallback to vbucks.png if image.png doesn't exist (safety)
    if not os.path.exists(image_path):
         image_path = os.path.join(bot_dir, "vbucks.png")

    view = TicketButton(ctx.guild.id)
    
    if os.path.exists(image_path):
        try:
            filename = os.path.basename(image_path)
            file = discord.File(image_path, filename=filename)
            embed.set_image(url=f"attachment://{filename}")
            await ctx.send(embed=embed, file=file, view=view)
        except Exception as e:
            print(f"[ERROR] Failed to send image: {e}")
            await ctx.send(embed=embed, view=view)
    else:
        # Web fallback if no local image
        embed.set_image(url="https://cdn2.unrealengine.com/fortnite-v-bucks-1920x1080-866247833.jpg")
        await ctx.send(embed=embed, view=view)


@bot.tree.command(name="vbucks", description="عرض أسعار الفيباكس (Show V-Bucks Prices)")
async def vbucks_slash(interaction: discord.Interaction):
    """Slash command to display V-Bucks Prices"""
    embed = discord.Embed(
        title="<:Vbucks:1470075477975630059> **FORTNITE V-BUCKS PRICES**",
        description="**Get your V-Bucks safely and instantly!** ⚡\n*Legal & Safe 100%*",
        color=0x9146FF # Purple Color
    )
    
    # Price List
    embed.add_field(
        name="💸 **Price List**",
        value=(
            "> **10,000 V-Bucks**  →  **400 DH**\n"
            "> **12,000 V-Bucks**  →  **480 DH**\n"
            "> **15,000 V-Bucks**  →  **600 DH**\n"
            "> **25,000 V-Bucks**  →  **1000 DH**\n"
            "> **50,000 V-Bucks**  →  **1800 DH**"
        ),
        inline=False
    )
    
    # Process
    embed.add_field(
        name="📝 **How to Buy?**",
        value=(
            "1️⃣ **Open Ticket** 📩 : Click button below\n"
            "2️⃣ **Payment** 💳 : <#1466153813323808849>\n"
            "3️⃣ **Delivery** 🚀 : Instant delivery to your account"
        ),
        inline=False
    )
    
    embed.set_footer(text="Karys Shop | Fortnite Services 🛒", icon_url=interaction.client.user.avatar.url if interaction.client.user.avatar else None)
    
    # Image handling logic (image.png in current dir)
    bot_dir = os.path.dirname(os.path.abspath(__file__))
    
    # User requested specific image: image.png for vbucks
    image_path = os.path.join(bot_dir, "image.png")
    
    # Fallback to vbucks.png if image.png doesn't exist
    if not os.path.exists(image_path):
         image_path = os.path.join(bot_dir, "vbucks.png")
    
    view = TicketButton(interaction.guild_id)
    
    if os.path.exists(image_path):
        try:
            filename = os.path.basename(image_path)
            file = discord.File(image_path, filename=filename)
            embed.set_image(url=f"attachment://{filename}")
            await interaction.response.send_message(embed=embed, file=file, view=view)
        except Exception as e:
            print(f"[ERROR] Failed to send image: {e}")
            await interaction.response.send_message(embed=embed, view=view)
    else:
        # Web fallback
        embed.set_image(url="https://cdn2.unrealengine.com/fortnite-v-bucks-1920x1080-866247833.jpg")
        await interaction.response.send_message(embed=embed, view=view)

@bot.command(name='scan')
@commands.has_permissions(administrator=True)
async def scan_accounts(ctx):
    """Scan for accounts created less than 1 month ago and timeout them"""
    await ctx.send("🔍 Scanning members... This might take a moment.")
    
    count_scanned = 0
    count_timed_out = 0
    timed_out_members = []
    
    # 1 month ago (30 days)
    # Ensure timezone awareness for comparison
    one_month_ago = datetime.now(timezone.utc) - timedelta(days=30)
    
    try:
        # Iterate over all members in the guild
        for member in ctx.guild.members:
            if member.bot:
                continue
                
            count_scanned += 1
            
            # Check if account creation date is less than 30 days ago
            # member.created_at is timezone-aware (UTC)
            if member.created_at > one_month_ago:
                try:
                    # Timeout for 7 days
                    await member.timeout(timedelta(days=7), reason="Account too new (< 1 month) - Auto Scan")
                    count_timed_out += 1
                    timed_out_members.append(member.mention)
                    print(f"[SCAN] Timed out {member.name} (Created: {member.created_at})")
                except discord.Forbidden:
                    print(f"[SCAN] Failed to timeout {member.name} (Missing permissions)")
                except Exception as e:
                    print(f"[SCAN] Error timing out {member.name}: {e}")
        
        # Prepare result message
        result_msg = f"✅ Scan complete.\n📊 **Results:**\n- Scanned: `{count_scanned}` members\n- Timed out: `{count_timed_out}` members (Account < 30 days old)\n- Timeout Duration: 7 Days"
        
        if count_timed_out > 0:
            result_msg += "\n\n**Timed Out Members:**"
            await ctx.send(result_msg)
            
            # Send members in chunks of 2000 characters
            chunk = ""
            for member_mention in timed_out_members:
                entry = f"• {member_mention}\n"
                if len(chunk) + len(entry) > 1900: # Leave some buffer
                    await ctx.send(chunk)
                    chunk = entry
                else:
                    chunk += entry
            
            if chunk:
                await ctx.send(chunk)
        else:
            await ctx.send(result_msg)
            
    except Exception as e:
        print(f"[ERROR] Scan failed: {e}")
        await ctx.send(f"❌ An error occurred during scan: {str(e)}")

@bot.command(name='remove')
@commands.has_permissions(administrator=True)
async def remove_timeouts(ctx):
    """Remove timeout from all members"""
    await ctx.send("🔓 Removing timeouts from all members... This might take a moment.")
    
    count_removed = 0
    
    try:
        # Iterate over all members in the guild
        for member in ctx.guild.members:
            if member.bot:
                continue
            
            # Check if member is timed out
            if member.is_timed_out():
                try:
                    # Remove timeout by setting it to None
                    await member.timeout(None, reason="Admin Remove Command")
                    count_removed += 1
                    print(f"[REMOVE] Removed timeout from {member.name}")
                except discord.Forbidden:
                    print(f"[REMOVE] Failed to remove timeout from {member.name} (Missing permissions)")
                except Exception as e:
                    print(f"[REMOVE] Error removing timeout from {member.name}: {e}")
        
        await ctx.send(f"✅ Removal complete.\n🔓 **Result:** Removed timeout from `{count_removed}` members.")
        
    except Exception as e:
        print(f"[ERROR] Remove failed: {e}")
        await ctx.send(f"❌ An error occurred during removal: {str(e)}")

@bot.command(name='setup_roles')
@commands.has_permissions(administrator=True)
async def setup_roles(ctx):
    """Create shop roles with no permissions"""
    await ctx.send("🛠️ Setting up roles...")
    
    # Define roles: Name, Color
    roles_to_create = [
        {"name": "👑・Mythic Clients", "color": 0x992D22},    # Dark Red
        {"name": "💎・Royalty +500$", "color": 0xE67E22},    # Dark Gold/Orange
        {"name": "🌟・Prestige +100$", "color": 0xF1C40F},   # Gold Yellow
        {"name": "🔮・Premium +50$", "color": 0x71368A}      # Dark Purple
    ]
    
    created_count = 0
    skipped_count = 0
    
    try:
        guild = ctx.guild
        for role_data in roles_to_create:
            existing_role = discord.utils.get(guild.roles, name=role_data["name"])
            
            if existing_role:
                # Update existing role
                await existing_role.edit(
                    color=discord.Color(role_data["color"]),
                    permissions=discord.Permissions.none(),
                    reason="Setup Roles Command - Update"
                )
                print(f"[ROLES] Updated role: {role_data['name']}")
                skipped_count += 1 # Counting as skipped for creation, but it is updated
            else:
                # Create role with NO permissions
                await guild.create_role(
                    name=role_data["name"],
                    color=discord.Color(role_data["color"]),
                    permissions=discord.Permissions.none(),
                    reason="Setup Roles Command - Create"
                )
                created_count += 1
                print(f"[ROLES] Created role: {role_data['name']}")
            
        await ctx.send(f"✅ Setup complete!\n✨ **Created:** `{created_count}` roles\n🔄 **Updated:** `{skipped_count}` roles")
        
    except Exception as e:
        print(f"[ERROR] Setup roles failed: {e}")
        await ctx.send(f"❌ An error occurred: {str(e)}")

@bot.command(name='bdal')
@commands.has_permissions(administrator=True)
async def change_role_name(ctx, old_name: str, new_name: str):
    """Change role name. Usage: !bdal "Old Name" "New Name" """
    role = discord.utils.get(ctx.guild.roles, name=old_name)
    
    if role:
        try:
            await role.edit(name=new_name, reason="Admin Rename Command")
            await ctx.send(f"✅ Role renamed successfully!\nOld: `{old_name}`\nNew: `{new_name}`")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to edit this role.")
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}")
    else:
        await ctx.send(f"❌ Role `{old_name}` not found!")

@change_role_name.error
async def change_role_name_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('❌ **Usage:** `!bdal "Old Name" "New Name"`\nExample: `!bdal "👑・Mythic Clients" "👑・King Clients"`')

@bot.command(name='say')
@commands.has_permissions(administrator=True)
async def say(ctx, *, message):
    """Make the bot say something"""
    try:
        await ctx.message.delete()
    except:
        pass
    await ctx.send(message)





@bot.command(name='ticket_panel')
@commands.has_permissions(administrator=True)
async def ticket_panel(ctx):
    """Deploy the ticket panel"""
    try:
        await ctx.message.delete()
    except:
        pass
    embed = discord.Embed(
        title="🛒 **KARYS SHOP | SUPPORT & ORDERS**",
        description=(
            "**Welcome to Karys Shop!** 🌟\n"
            "مرحباً بكم في متجر كاريس! 🇲🇦\n\n"
            "**Open a ticket for:**\n"
            "💸 **Buying & Selling** (Accounts, Points, Nitro)\n"
            "🛠️ **Support & Assistance**\n"
            "🤝 **Business Inquiries**\n\n"
            "*Click the button below to start your transaction!* 📩"
        ),
        color=0xFF0000
    )
    
    # Image handling logic (karys.png in current dir)
    bot_dir = os.path.dirname(os.path.abspath(__file__))
    karys_image_path = os.path.join(bot_dir, "karys.png")
    
    if os.path.exists(karys_image_path):
        try:
            file = discord.File(karys_image_path, filename="karys.png")
            embed.set_thumbnail(url="attachment://karys.png")
            await ctx.send(embed=embed, file=file, view=TicketSystemView())
        except Exception as e:
            print(f"[ERROR] Failed to send image: {e}")
            await ctx.send(embed=embed, view=TicketSystemView())

@bot.tree.command(name="ticket_panel", description="Deploy the ticket panel (Admin Only)")
async def ticket_panel_slash(interaction: discord.Interaction):
    """Slash command to deploy ticket panel"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Admin only.", ephemeral=True)
        return
        
    await interaction.response.defer()
    await interaction.delete_original_response() # Delete the "thinking" message if possible or just send new one
    
    # Actually we want to send a new message that stays, so we shouldn't delete original response if we used defer()
    # But for a panel, we usually want it to look clean. Slash commands always leave a trace unless ephemeral.
    # Let's just send the panel as a new message.
    
    embed = discord.Embed(
        title="🛒 **KARYS SHOP | SUPPORT & ORDERS**",
        description=(
            "**Welcome to Karys Shop!** 🌟\n"
            "مرحباً بكم في متجر كاريس! 🇲🇦\n\n"
            "**Open a ticket for:**\n"
            "💸 **Buying & Selling** (Accounts, Points, Nitro)\n"
            "🛠️ **Support & Assistance**\n"
            "🤝 **Business Inquiries**\n\n"
            "*Click the button below to start your transaction!* 📩"
        ),
        color=0xFF0000
    )
    
    # Image handling logic (karys.png in current dir)
    bot_dir = os.path.dirname(os.path.abspath(__file__))
    karys_image_path = os.path.join(bot_dir, "karys.png")
    
    channel = interaction.channel
    
    if os.path.exists(karys_image_path):
        try:
            file = discord.File(karys_image_path, filename="karys.png")
            embed.set_thumbnail(url="attachment://karys.png")
            await channel.send(embed=embed, file=file, view=TicketSystemView())
        except Exception as e:
            print(f"[ERROR] Failed to send image: {e}")
            await channel.send(embed=embed, view=TicketSystemView())
    else:
        # Fallback to just embed
        await channel.send(embed=embed, view=TicketSystemView())


# --- Utility Commands ---

@bot.command(name="sync")
async def sync(ctx):
    """Sync slash commands manually"""
    if ctx.author.guild_permissions.administrator:
        try:
            synced = await bot.tree.sync()
            await ctx.send(f"✅ Synced {len(synced)} slash commands.")
        except Exception as e:
            await ctx.send(f"❌ Error syncing: {e}")
    else:
        await ctx.send("❌ You do not have permission to use this command.")

# --- New Feature Slash Commands ---

# !setup-reviews: Create/update the reviews channel with correct role permissions
@bot.command(name="setup-reviews", aliases=["setupreviews"])
async def setup_reviews_cmd(ctx):
    """Admin only: Create a #reviews channel where Customers & VIP roles can write."""
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ Admin only.")
        return

    guild = ctx.guild

    # The roles that are allowed to WRITE reviews
    allowed_role_names = ["Customers", "$50 Dollar", "$100 Dollar", "$500 Dollar", "50$", "100$", "500$", "50 Dollar", "100 Dollar", "500 Dollar"]

    # Find matching roles (case-insensitive)
    allowed_roles = []
    for role in guild.roles:
        for name in allowed_role_names:
            if role.name.lower() == name.lower():
                allowed_roles.append(role)
                break

    if not allowed_roles:
        await ctx.send("⚠️ Ma-l9it-ch les roles! Ta9dar t-smih chi wa7da mn: `Customers`, `$50 Dollar`, `$100 Dollar`, `$500 Dollar`")
        return

    # Find or create the reviews channel
    channel = discord.utils.get(guild.text_channels, name="⭐・reviews")
    if not channel:
        channel = discord.utils.get(guild.text_channels, name="reviews")

    # Build permission overwrites
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=False,   # Can READ only
            read_message_history=True
        ),
        guild.me: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            manage_messages=True
        )
    }

    # Allow allowed roles to write
    for role in allowed_roles:
        overwrites[role] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            embed_links=True,
            attach_files=True
        )

    if channel:
        # Update existing channel permissions
        await channel.edit(overwrites=overwrites, reason="!setup-reviews: Updated permissions")
        await ctx.send(f"✅ Channel {channel.mention} updated!\n**Can write:** " + ", ".join(f"`{r.name}`" for r in allowed_roles))
    else:
        # Find the INFO or main category
        category = discord.utils.get(guild.categories, name="〢─ INFO ─〢")
        if not category:
            category = discord.utils.get(guild.categories, name="INFO")

        channel = await guild.create_text_channel(
            "⭐・reviews",
            category=category,
            overwrites=overwrites,
            topic="🌟 Share your experience with Karys Shop! | Customers & VIP only"
        )

        # Post a welcome message
        embed = discord.Embed(
            title="⭐ Reviews — Karys Shop",
            description=(
                "**Share your experience with us!**\n\n"
                "✅ Only customers with an order can leave a review.\n"
                "🚫 Fake reviews or spam will result in a timeout.\n\n"
                "*Thank you for trusting Karys Shop! 🙏*"
            ),
            color=0xF1C40F
        )
        embed.set_footer(text="Karys Shop | Reviews")
        await channel.send(embed=embed)

        await ctx.send(f"✅ Channel {channel.mention} created!\n**Can write:** " + ", ".join(f"`{r.name}`" for r in allowed_roles))

# !move-logs: Move all channels FROM Tickets/Orders categories INTO the LOGS X categories below
@bot.command(name="move-logs", aliases=["movelogs"])
async def move_logs_cmd(ctx):
    """Admin only: Move closed tickets from top categories INTO LOGS categories."""
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ Admin only.")
        return

    await ctx.send("⏳ Starting migration of tickets INTO the LOGS categories...")
    guild = ctx.guild
    moved = 0
    errors = 0

    # 1. Find all TARGET LOGS categories (destinations)
    logs_cats = []
    for cat in guild.categories:
        if "LOGS" in cat.name.upper():
            match = re.search(r'LOGS\s*(\d+)', cat.name, re.IGNORECASE)
            if match:
                num = int(match.group(1))
                logs_cats.append((num, cat))
    logs_cats.sort(key=lambda x: x[0])

    if not logs_cats:
        await ctx.send("❌ Ma-kayna 7ta category dyal LOGS (bhal 🛡️ LOGS 1).")
        return

    # 2. Find Source tickets (Tickets that are NOT in a LOGS category and are named like a ticket)
    tickets_to_move = []
    
    # Prefix for identifying tickets:
    valid_prefixes = ["ticket-", "order-", "closedorder-", "closed-"]
    
    for channel in guild.text_channels:
        # If the channel matches ticket naming conventions
        if any(channel.name.startswith(p) for p in valid_prefixes):
            # Check if it is NOT currently in a LOGS category
            in_logs = False
            if channel.category and "LOGS" in channel.category.name.upper():
                in_logs = True
                
            if not in_logs:
                tickets_to_move.append(channel)

    if not tickets_to_move:
        await ctx.send("✅ Ma-l9it 7ta ticket l-fouq li khas-ha temchi l-LOGS! Kolchi m9ad.")
        return

    dest_idx = 0

    for channel in tickets_to_move:
        # Find the next available LOGS category (max 50 per category)
        while dest_idx < len(logs_cats) and len(logs_cats[dest_idx][1].channels) >= 50:
            dest_idx += 1
            
        # If we ran out of LOGS categories, create a new one!
        if dest_idx >= len(logs_cats):
            # Calculate next number
            next_num = (logs_cats[-1][0] + 1) if logs_cats else 1
            
            # Create new category
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False)
            }
            new_cat_name = f"🛡️ LOGS {next_num}"
            try:
                new_cat = await guild.create_category(new_cat_name, overwrites=overwrites)
                logs_cats.append((next_num, new_cat))
                dest_cat = new_cat
            except Exception as e:
                await ctx.send(f"❌ Error creating new category: {e}")
                break
        else:
            dest_cat = logs_cats[dest_idx][1]
            
        try:
            await channel.edit(category=dest_cat)
            moved += 1
            await asyncio.sleep(0.8)  # Rate limit
        except Exception as e:
            print(f"[move-logs] Error moving {channel.name}: {e}")
            errors += 1

    await ctx.send(f"✅ Migration done! **{moved}** tickets moved to LOGS, **{errors}** errors.")


# Prefix command version: !scan-fakes
@bot.command(name="scan-fakes")
async def scan_fakes_prefix(ctx):
    """List accounts with age < 60 days and no avatar. Admin only."""
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ Admin only.")
        return
    
    fakes = []
    now = datetime.now(timezone.utc)
    
    for member in ctx.guild.members:
        if member.bot: continue
        age = (now - member.created_at).days
        if age < 60 and member.avatar is None:
            fakes.append(member)

    if not fakes:
        await ctx.send("✅ Ma-kaynin-ch les comptes suspects (Account < 60 jours + Bla tswira).")
        return

    # Build report embed
    embed = discord.Embed(
        title=f"🔍 Suspicious Accounts — {len(fakes)} Found",
        color=0xFF4444,
        timestamp=datetime.now()
    )
    
    lines = ""
    for m in fakes[:25]:
        age_days = (now - m.created_at).days
        lines += f"• {m.mention} `{m}` | 📅 {age_days} jours\n"
    
    if len(fakes) > 25:
        lines += f"\n*...o {len(fakes)-25} kbar...*"
    
    embed.description = lines
    embed.set_footer(text="Karys Shop Auto-Mod | Accounts < 60 days & No Avatar")

    class FakeActionView(discord.ui.View):
        def __init__(self, fakes_list):
            super().__init__(timeout=120)
            self.fakes = fakes_list

        @discord.ui.button(label=f"⏱️ Timeout All (7 Days)", style=discord.ButtonStyle.danger, emoji="🔨")
        async def timeout_all(self, btn_interaction: discord.Interaction, button: discord.ui.Button):
            if not btn_interaction.user.guild_permissions.administrator:
                await btn_interaction.response.send_message("❌ Admin only.", ephemeral=True)
                return
            await btn_interaction.response.defer(ephemeral=True)
            count = 0
            for m in self.fakes:
                try:
                    await m.timeout(timedelta(days=7), reason="!scan-fakes: Account < 60 days & No Avatar")
                    count += 1
                    await asyncio.sleep(0.5)  # Avoid rate limits
                except:
                    pass
            await btn_interaction.followup.send(f"✅ Timeout directory on **{count}** accounts.", ephemeral=True)
            self.stop()

        @discord.ui.button(label="🚫 Cancel", style=discord.ButtonStyle.secondary)
        async def cancel(self, btn_interaction: discord.Interaction, button: discord.ui.Button):
            await btn_interaction.response.send_message("❌ Cancelled.", ephemeral=True)
            self.stop()

    await ctx.send(embed=embed, view=FakeActionView(fakes))

@bot.tree.command(name="rps", description="Play Rock Paper Scissors with the bot!")
async def rps(interaction: discord.Interaction):
    view = RPSView(interaction.user)
    embed = discord.Embed(
        title="Rock Paper Scissors",
        description="Choose your move below!",
        color=0x9B59B6
    )
    await interaction.response.send_message(embed=embed, view=view)



@bot.tree.command(name="set-invite-leaderboard", description="Set up the invite leaderboard system!")
@discord.app_commands.default_permissions(administrator=True)
async def set_invite_leaderboard(interaction: discord.Interaction):
    await interaction.response.send_message("🛠️ This feature is under construction.", ephemeral=True)

@bot.tree.command(name="set-message-leaderboard", description="Set up the message leaderboard system!")
@discord.app_commands.default_permissions(administrator=True)
async def set_message_leaderboard(interaction: discord.Interaction):
    await interaction.response.send_message("🛠️ This feature is under construction.", ephemeral=True)

@bot.tree.command(name="set-antilink-system", description="Set the anti-link system the way you want it!")
@discord.app_commands.default_permissions(administrator=True)
async def set_antilink_system(interaction: discord.Interaction):
    # Currently hardcoded in on_message, but this UI can expand it
    await interaction.response.send_message("🛡️ Anti-link is currently active. UI Settings coming soon.", ephemeral=True)

@bot.tree.command(name="set-auto-message", description="Set the auto-message system!")
@discord.app_commands.default_permissions(administrator=True)
async def set_auto_message(interaction: discord.Interaction):
    await interaction.response.send_message("🛠️ This feature is under construction.", ephemeral=True)

# --- World Mood Commands ---
@bot.tree.command(name="setup-worldmood", description="Setup the World Mood channel under welcome!")
@discord.app_commands.default_permissions(administrator=True)
async def setup_worldmood(interaction: discord.Interaction):
    guild = interaction.guild
    welcome_channel = discord.utils.get(guild.text_channels, name="welcome")
    
    if not welcome_channel:
        # Fallback if there is no channel named exactly 'welcome'
        category = interaction.channel.category
        position = 0
    else:
        category = welcome_channel.category
        position = welcome_channel.position + 1

    try:
        new_channel = await guild.create_text_channel(
            name="world-mood",
            category=category,
            position=position,
            topic="يحلل تويتر ويقول كيفاش مزاج العالم اليوم (World Mood Analysis)"
        )
        embed = discord.Embed(
            title="🌍 World Mood Channel Setup",
            description=f"✅ Created channel {new_channel.mention} successfully!\nIt is placed right below the welcome channel.",
            color=0x2ECC71
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to create channels in this server.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error creating channel: {e}", ephemeral=True)

# Make sure loop tracking is active
world_mood_loop_running = False

@tasks.loop(hours=10)
async def world_mood_auto_post():
    # Only try to post if the welcome/world-mood channel exists
    for guild in bot.guilds:
        channel = discord.utils.get(guild.text_channels, name="world-mood")
        if not channel:
            continue
            
        news_items = [
            {
                "category": "🚀 Technology & AI",
                "headline": "New AI Model Surpasses Human Performance in Complex Coding Tasks!",
                "arabic": "نموذج ذكاء اصطناعي جديد يتخطى القدرات البشرية في البرمجة المعقدة!",
                "details": "Major tech companies announced today that their latest AI can write full-stack applications in seconds.",
                "color": 0x3498DB,
                "icon": "https://cdn-icons-png.flaticon.com/512/2083/2083213.png"
            },
            {
                "category": "🌍 Global Events",
                "headline": "Historic Peace Treaty Signed Ending Decade-Long Conflict",
                "arabic": "توقيع معاهدة سلام تاريخية تنهي صراعاً دام عقداً كاملاً",
                "details": "Leaders from major nations gathered today in a historic summit, bringing hope to millions.",
                "color": 0x2ECC71,
                "icon": "https://cdn-icons-png.flaticon.com/512/814/814513.png"
            },
            {
                "category": "🎮 Gaming News",
                "headline": "GTA 6 Trailer Breaks the Internet Once Again!",
                "arabic": "تريلر لعبة GTA 6 يكسر الإنترنت مجدداً بقوة!",
                "details": "Rockstar dropped a surprise second trailer, confirming the exact release month and showcasing incredible graphics.",
                "color": 0xE74C3C,
                "icon": "https://cdn-icons-png.flaticon.com/512/808/808476.png"
            },
            {
                "category": "💰 Economy & Crypto",
                "headline": "Bitcoin Reaches Unprecedented New All-Time High!",
                "arabic": "البيتكوين يحطم الأرقام القياسية ويصل لأعلى مستوى له في التاريخ!",
                "details": "Cryptocurrency markets surged today following major institutional adoptions globally.",
                "color": 0xF1C40F,
                "icon": "https://cdn-icons-png.flaticon.com/512/2590/2590518.png"
            },
            {
                "category": "⚽ Sports",
                "headline": "A Shocking Transfer Shakes the Football World!",
                "arabic": "صفقة انتقال صادمة تهز عالم كرة القدم تماماً!",
                "details": "One of the world's top players has just signed a record-breaking deal with an unexpected club.",
                "color": 0x27AE60,
                "icon": "https://cdn-icons-png.flaticon.com/512/1165/1165187.png"
            },
            {
                "category": "🌌 Space Exploration",
                "headline": "James Webb Telescope Discovers Potentially Habitable Exoplanet",
                "arabic": "تلسكوب جيمس ويب يكتشف كوكباً خارجياً قد يكون صالحاً للحياة",
                "details": "NASA confirmed the discovery of an Earth-sized planet with signs of water vapor in its atmosphere.",
                "color": 0x9B59B6,
                "icon": "https://cdn-icons-png.flaticon.com/512/3254/3254068.png"
            }
        ]
        
        todays_news = random.sample(news_items, k=random.randint(2, 3))
        embed = discord.Embed(
            title="📰 World News Auto-Broadcast - نشرة أخبار العالم",
            description="Here is what is happening around the globe right now:\nإليك أبرز ما يحدث في العالم هذه اللحظة:",
            color=todays_news[0]["color"]
        )
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/2965/2965879.png")
        for i, news in enumerate(todays_news, 1):
            content = f"**{news['headline']}**\n{news['arabic']}\n*_{news['details']}_*"
            embed.add_field(name=f"{news['category']}", value=content, inline=False)
            
        embed.set_footer(text="Powered by Karys AI • Simulated Live News Sync")
        try:
            await channel.send(embed=embed)
        except Exception:
            pass

@bot.tree.command(name="worldmood", description="Discover what's happening in the world today! Starts auto-broadcast.")
async def worldmood(interaction: discord.Interaction):
    global world_mood_loop_running
    
    if not world_mood_loop_running:
        world_mood_auto_post.start()
        world_mood_loop_running = True
        init_message = "✅ Auto-News Broadcast started! It will now auto-post to `#world-mood` every 10 hours.\nتم تفعيل النشر التلقائي كل 10 ساعات في غرفة `#world-mood`."
    else:
        init_message = "♻️ The auto-broadcast is already running in the background."

    # Send an initial burst to the exact channel they triggered it in
    # Simulated top world news to avoid forcing the user to get an API key
    news_items = [
        {
            "category": "🚀 Technology & AI",
            "headline": "New AI Model Surpasses Human Performance in Complex Coding Tasks!",
            "arabic": "نموذج ذكاء اصطناعي جديد يتخطى القدرات البشرية في البرمجة المعقدة!",
            "details": "Major tech companies announced today that their latest AI can write full-stack applications in seconds.",
            "color": 0x3498DB,
            "icon": "https://cdn-icons-png.flaticon.com/512/2083/2083213.png"
        },
        {
            "category": "🌍 Global Events",
            "headline": "Historic Peace Treaty Signed Ending Decade-Long Conflict",
            "arabic": "توقيع معاهدة سلام تاريخية تنهي صراعاً دام عقداً كاملاً",
            "details": "Leaders from major nations gathered today in a historic summit, bringing hope to millions.",
            "color": 0x2ECC71,
            "icon": "https://cdn-icons-png.flaticon.com/512/814/814513.png"
        },
        {
            "category": "🎮 Gaming News",
            "headline": "GTA 6 Trailer Breaks the Internet Once Again!",
            "arabic": "تريلر لعبة GTA 6 يكسر الإنترنت مجدداً بقوة!",
            "details": "Rockstar dropped a surprise second trailer, confirming the exact release month and showcasing incredible graphics.",
            "color": 0xE74C3C,
            "icon": "https://cdn-icons-png.flaticon.com/512/808/808476.png"
        },
        {
            "category": "💰 Economy & Crypto",
            "headline": "Bitcoin Reaches Unprecedented New All-Time High!",
            "arabic": "البيتكوين يحطم الأرقام القياسية ويصل لأعلى مستوى له في التاريخ!",
            "details": "Cryptocurrency markets surged today following major institutional adoptions globally.",
            "color": 0xF1C40F,
            "icon": "https://cdn-icons-png.flaticon.com/512/2590/2590518.png"
        },
        {
            "category": "⚽ Sports",
            "headline": "A Shocking Transfer Shakes the Football World!",
            "arabic": "صفقة انتقال صادمة تهز عالم كرة القدم تماماً!",
            "details": "One of the world's top players has just signed a record-breaking deal with an unexpected club.",
            "color": 0x27AE60,
            "icon": "https://cdn-icons-png.flaticon.com/512/1165/1165187.png"
        },
        {
            "category": "🌌 Space Exploration",
            "headline": "James Webb Telescope Discovers Potentially Habitable Exoplanet",
            "arabic": "تلسكوب جيمس ويب يكتشف كوكباً خارجياً قد يكون صالحاً للحياة",
            "details": "NASA confirmed the discovery of an Earth-sized planet with signs of water vapor in its atmosphere.",
            "color": 0x9B59B6,
            "icon": "https://cdn-icons-png.flaticon.com/512/3254/3254068.png"
        }
    ]
    # Pick 2-3 random news stories for the day
    todays_news = random.sample(news_items, k=random.randint(2, 3))
    
    embed = discord.Embed(
        title="📰 World News & Mood - أبرز أحداث العالم",
        description="Here is what is happening around the globe today:\nإليك أبرز ما يحدث في العالم اليوم:",
        color=todays_news[0]["color"] # Use color from top story
    )
    
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/2965/2965879.png")
    
    for i, news in enumerate(todays_news, 1):
        content = f"**{news['headline']}**\n{news['arabic']}\n*_{news['details']}_*"
        embed.add_field(name=f"{news['category']}", value=content, inline=False)
        
    embed.set_footer(text="Powered by Karys AI • Simulated Live News Sync")
    
    # Let user know the loop status
    await interaction.response.send_message(content=init_message, embed=embed)

@bot.tree.command(name="set-auto-reaction", description="Set the auto-reaction system!")
@discord.app_commands.default_permissions(administrator=True)
async def set_auto_reaction(interaction: discord.Interaction):
    await interaction.response.send_message("🛠️ This feature is under construction.", ephemeral=True)

@bot.tree.command(name="set-booster-channel", description="Set the booster channel system!")
@discord.app_commands.default_permissions(administrator=True)
async def set_booster_channel(interaction: discord.Interaction):
    await interaction.response.send_message("🛠️ This feature is under construction.", ephemeral=True)



@bot.command(name="giveaway")
async def giveaway_prefix(ctx):
    await ctx.send("⚠️ **Please use the new slash commands:**\n`/gcreate` - Start a new giveaway\n`/gend` - End a giveaway\n`/glist` - List active giveaways")

@bot.command(name="invites")
async def invites_prefix(ctx):
    await ctx.send("⚠️ **Please use the slash command:** `/invites`")

# --- Giveaway Commands ---

@bot.tree.command(name="invites", description="Check your invites or another user's")
async def invites(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    user_id = str(target.id)
    
    if user_id not in invites_data:
        invites_data[user_id] = {"regular": 0, "fake": 0, "bonus": 0, "leaves": 0}
        
    data = invites_data[user_id]
    total = (data["regular"] + data["bonus"]) - (data["leaves"] + data["fake"])
    if total < 0: total = 0
    
    embed = discord.Embed(title=f"✉️ Invites for {target.name}", color=0x3498DB)
    embed.add_field(name="Total Valid", value=f"**{total}**", inline=False)
    embed.add_field(name="Details", value=f"✅ Regular: {data['regular']}\n🎁 Bonus: {data['bonus']}\n🚪 Left: {data['leaves']}\n❌ Fake: {data['fake']}", inline=False)
    
    await interaction.response.send_message(embed=embed)

# --- Giveaway Commands (Top-Level) ---

@bot.tree.command(name="gcreate", description="Start a new giveaway")
@discord.app_commands.describe(
    prize="Prize description",
    winners="Number of winners",
    duration="Duration (e.g. 1m, 1h, 1d)",
    channel="Channel to host the giveaway in (Optional)",
    required_invites="Invites required to join (Optional)",
    description="Extra description (Optional)"
)
async def gcreate(interaction: discord.Interaction, prize: str, winners: int, duration: str, channel: discord.TextChannel = None, required_invites: int = 0, description: str = None):
    # Parse duration
    time_units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    try:
        unit = duration[-1].lower()
        value = int(duration[:-1])
        if unit not in time_units:
            raise ValueError
        seconds = value * time_units[unit]
    except:
            await interaction.response.send_message("❌ Invalid duration format. Use 10m, 1h, 1d etc.", ephemeral=True)
            return

    target_channel = channel or interaction.channel
    
    # Check permissions
    permissions = target_channel.permissions_for(interaction.guild.me)
    if not permissions.send_messages or not permissions.embed_links:
            await interaction.response.send_message(f"❌ I don't have permission to talk in {target_channel.mention}", ephemeral=True)
            return

    end_time = datetime.now() + timedelta(seconds=seconds)
    timestamp = int(end_time.timestamp())
    
    desc_text = f"React with the button to join!\n\n**Ends:** <t:{timestamp}:R>\n**Hosted by:** {interaction.user.mention}"
    if description:
        desc_text = f"{description}\n\n" + desc_text

    embed = discord.Embed(title=f"🎉 **GIVEAWAY: {prize}** 🎉", description=desc_text, color=0xFF00FF)
    if winners > 1:
        embed.add_field(name="🏆 Winners", value=f"{winners}", inline=True)
    
    if required_invites > 0:
        embed.add_field(name="📨 Required Invites", value=f"{required_invites}", inline=True)
        
    embed.add_field(name="👥 Entries", value="0", inline=True)
    
    embed.set_footer(text=f"Ends at")
    embed.timestamp = end_time
    
    await interaction.response.send_message(f"✅ Giveaway created in {target_channel.mention}", ephemeral=True)
    message = await target_channel.send(embed=embed)
    
    # Save giveaway
    giveaways_data[str(message.id)] = {
        "channel_id": target_channel.id,
        "prize": prize,
        "winners": winners,
        "required_invites": required_invites,
        "end_time": timestamp,
        "participants": [],
        "ended": False
    }
    save_data('giveaways.json', giveaways_data)
    
    # Add View
    await message.edit(view=GiveawayJoinButton(str(message.id), required_invites))
    
    # Background task to end giveaway
    bot.loop.create_task(schedule_giveaway_end(message.id, seconds))

@bot.tree.command(name="gend", description="End a running giveaway immediately")
@discord.app_commands.describe(message_id="Message ID of the giveaway")
async def gend(interaction: discord.Interaction, message_id: str):
    if not message_id:
        await interaction.response.send_message("❌ Please provide the Message ID.", ephemeral=True)
        return
    
    # Check if giveaway exists
    if message_id not in giveaways_data:
            await interaction.response.send_message("❌ Giveaway not found.", ephemeral=True)
            return

    if giveaways_data[message_id]["ended"]:
            await interaction.response.send_message("❌ This giveaway has already ended.", ephemeral=True)
            return

    await interaction.response.send_message("✅ Ending giveaway...", ephemeral=True)
    await end_giveaway_logic(message_id)

@bot.tree.command(name="greroll", description="Pick new winners for a giveaway")
@discord.app_commands.describe(message_id="Message ID of the giveaway", winners="Number of new winners (Optional)")
async def greroll(interaction: discord.Interaction, message_id: str, winners: int = 1):
    if not message_id:
        await interaction.response.send_message("❌ Please provide the Message ID.", ephemeral=True)
        return
    
    await reroll_giveaway(interaction, message_id, winners)

@bot.tree.command(name="glist", description="List active giveaways")
async def glist(interaction: discord.Interaction):
    active_giveaways = [gid for gid, data in giveaways_data.items() if not data["ended"]]
    if not active_giveaways:
        await interaction.response.send_message("No active giveaways.", ephemeral=True)
        return
        
    msg = "**Active Giveaways:**\n"
    for gid in active_giveaways:
        data = giveaways_data[gid]
        channel = interaction.guild.get_channel(data["channel_id"])
        channel_mention = channel.mention if channel else "Unknown Channel"
        msg += f"- 🆔 `{gid}` | 🎁 **{data['prize']}** | 📍 {channel_mention} | ⏳ <t:{data['end_time']}:R>\n"
    
    await interaction.response.send_message(msg, ephemeral=True)

@bot.tree.command(name="gparticipants", description="Show giveaway participants (Admin Only)")
@discord.app_commands.describe(message_id="Message ID of the giveaway")
async def gparticipants(interaction: discord.Interaction, message_id: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Admin only.", ephemeral=True)
        return

    if message_id not in giveaways_data:
            await interaction.response.send_message("❌ Giveaway not found.", ephemeral=True)
            return
            
    participants = giveaways_data[message_id]["participants"]
    if not participants:
        await interaction.response.send_message("❌ No participants yet.", ephemeral=True)
        return

    count = len(participants)
    user_list = ", ".join([f"<@{uid}>" for uid in participants[:80]]) # Limit to avoid 2000 char limit
    
    embed = discord.Embed(title=f"👥 Participants ({count})", description=user_list, color=0x00FF00)
    if count > 80:
        embed.set_footer(text=f"And {count-80} more...")
        
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="gchance", description="Add bonus chances to a user (Admin Only)")
@discord.app_commands.describe(user="User to manage", amount="Amount to add")
async def gchance(interaction: discord.Interaction, user: discord.Member, amount: int):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Admin only.", ephemeral=True)
        return

    user_id = str(user.id)
    if user_id not in invites_data:
        invites_data[user_id] = {"regular": 0, "fake": 0, "bonus": 0, "leaves": 0}
    
    invites_data[user_id]["bonus"] += amount
    save_data('invites.json', invites_data)

    await interaction.response.send_message(f"✅ Added **{amount}** bonus chances to {user.mention}. Total Bonus: {invites_data[user_id]['bonus']}", ephemeral=True)

async def schedule_giveaway_end(message_id, delay):
    await asyncio.sleep(delay)
    await end_giveaway_logic(message_id)

async def end_giveaway_logic(message_id):
    message_id = str(message_id)
    if message_id not in giveaways_data or giveaways_data[message_id]["ended"]:
        return

    data = giveaways_data[message_id]
    channel = bot.get_channel(data["channel_id"])
    
    if channel:
        try:
            message = await channel.fetch_message(int(message_id))
            
            # Select winners
            participants = data["participants"]
            winners_count = data["winners"]
            
            if not participants:
                await message.reply("❌ **Giveaway Ended:** No one joined.")
                data["ended"] = True
                save_data('giveaways.json', giveaways_data)
                return

            # Logic for chances: Simple pool expansion (User ID * Chance)
            weighted_pool = []
            for uid in participants:
                # Base chance = 1
                chance = 1
                uid_str = str(uid)
                if uid_str in invites_data:
                    chance += invites_data[uid_str].get("bonus", 0)
                
                if chance < 1: chance = 1 
                
                # Add to pool
                weighted_pool.extend([uid] * chance)
            
            winners = []
            if len(participants) < winners_count:
                winners = participants # Everyone wins
            else:
                 try:
                     temp_pool = weighted_pool.copy()
                     for _ in range(winners_count):
                         if not temp_pool: break
                         winner = random.choice(temp_pool)
                         winners.append(winner)
                         temp_pool = [x for x in temp_pool if x != winner]
                 except:
                     winners = [random.choice(participants)]

            winners_mentions = ", ".join([f"<@{uid}>" for uid in winners])
            
            embed = message.embeds[0]
            embed.color = 0x2ECC71
            embed.title = "🎉 **GIVEAWAY ENDED** 🎉"
            embed.description = f"**Prize:** {data['prize']}\n**Winners:** {winners_mentions}"
            embed.set_footer(text="Ended")
            
            await message.edit(embed=embed, view=None) # Remove button
            await message.reply(f"🎉 **Congratulations** {winners_mentions}! You won **{data['prize']}**!")
            
            data["ended"] = True
            data["winners_list"] = winners
            save_data('giveaways.json', giveaways_data)

        except Exception as e:
            print(f"Error ending giveaway: {e}")

async def reroll_giveaway(interaction, message_id, winners_count):
    message_id = str(message_id)
    if message_id not in giveaways_data:
        await interaction.response.send_message("❌ Giveaway not found.", ephemeral=True)
        return

    data = giveaways_data[message_id]
    participants = data["participants"]
    
    if not participants:
        await interaction.response.send_message("❌ No participants to reroll.", ephemeral=True)
        return

    # Weighted Logic again
    weighted_pool = []
    for uid in participants:
        chance = 1
        if uid in invites_data:
            chance += invites_data[uid]["bonus"]
        if chance < 1: chance = 1 
        weighted_pool.extend([uid] * chance)
    
    winners = []
    temp_pool = weighted_pool.copy()
    
    for _ in range(winners_count):
        if not temp_pool: break
        winner = random.choice(temp_pool)
        winners.append(winner)
        temp_pool = [x for x in temp_pool if x != winner]

    winners_mentions = ", ".join([f"<@{uid}>" for uid in winners])
    await interaction.channel.send(f"🎉 **New Winner(s):** {winners_mentions}!")
    
    await interaction.response.send_message("✅ Rerolled.", ephemeral=True)


# --- Invite Tracking Events ---

@bot.event
async def on_invite_create(invite):
    if invite.guild.id not in invite_cache:
        invite_cache[invite.guild.id] = []
    # Refresh cache for this guild
    invite_cache[invite.guild.id] = await invite.guild.invites()

@bot.event
async def on_invite_delete(invite):
    if invite.guild.id in invite_cache:
        invite_cache[invite.guild.id] = await invite.guild.invites()

@bot.event
async def on_member_join(member):
    # Find inviter
    inviter = None
    try:
        current_invites = await member.guild.invites()
        cached_invites = invite_cache.get(member.guild.id, [])
        
        for invite in current_invites:
            for cached in cached_invites:
                if invite.code == cached.code and invite.uses > cached.uses:
                    inviter = invite.inviter
                    break
            if inviter: break
        
        invite_cache[member.guild.id] = current_invites
        
        if inviter:
            inviter_id = str(inviter.id)
            if inviter_id not in invites_data:
                invites_data[inviter_id] = {"regular": 0, "fake": 0, "bonus": 0, "leaves": 0}
            
            # Check for fake (account age < 3 days?)
            if (datetime.now(timezone.utc) - member.created_at).days < 3:
                invites_data[inviter_id]["fake"] += 1
            else:
                invites_data[inviter_id]["regular"] += 1
                
            save_data('invites.json', invites_data)
            
    except Exception as e:
        print(f"Error tracking invite: {e}")

@bot.event
async def on_member_remove(member):
    # Track leaves in invites.json
    try:
        # Find who invited them or just track the leave
        # For now, just log the leave
        embed = discord.Embed(
            title="📥 Member Left",
            description=f"**{member}** has left the server.",
            color=0xE74C3C,
            timestamp=datetime.now()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.add_field(name="User ID", value=f"`{member.id}`", inline=True)
        
        # Determine log channel
        log_channel = discord.utils.get(member.guild.text_channels, name="👥・member-logs")
        if log_channel:
            await log_channel.send(embed=embed)
    except Exception as e:
        print(f"Error in on_member_remove log: {e}")

@bot.event
async def on_message_delete(message):
    if message.author.bot: return
    try:
        embed = discord.Embed(
            title="🗑️ Message Deleted",
            description=f"**Author:** {message.author.mention}\n**Channel:** {message.channel.mention}",
            color=0xE74C3C,
            timestamp=datetime.now()
        )
        content = message.content[:1000] or "*No text content (likely an image or embed)*"
        embed.add_field(name="Content", value=content, inline=False)
        
        log_channel = discord.utils.get(message.guild.text_channels, name="💬・message-logs")
        if log_channel:
            await log_channel.send(embed=embed)
    except Exception as e:
        print(f"Error in on_message_delete log: {e}")

@bot.event
async def on_message_edit(before, after):
    if before.author.bot or before.content == after.content: return
    try:
        embed = discord.Embed(
            title="📝 Message Edited",
            description=f"**Author:** {before.author.mention}\n**Channel:** {before.channel.mention}\n[Jump to message]({after.jump_url})",
            color=0xF1C40F,
            timestamp=datetime.now()
        )
        embed.add_field(name="Before", value=before.content[:1000] or "*Empty*", inline=False)
        embed.add_field(name="After", value=after.content[:1000] or "*Empty*", inline=False)
        
        log_channel = discord.utils.get(before.guild.text_channels, name="💬・message-logs")
        if log_channel:
            await log_channel.send(embed=embed)
    except Exception as e:
        print(f"Error in on_message_edit log: {e}")

@bot.event
async def on_member_ban(guild, user):
    try:
        embed = discord.Embed(
            title="🔨 Member Banned",
            description=f"**User:** {user.mention} ({user})",
            color=0xFF0000,
            timestamp=datetime.now()
        )
        embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)
        embed.add_field(name="User ID", value=f"`{user.id}`", inline=True)
        
        log_channel = discord.utils.get(guild.text_channels, name="⚖️・moderation-logs")
        if log_channel:
            await log_channel.send(embed=embed)
    except Exception as e:
        print(f"Error in on_member_ban log: {e}")

@bot.event
async def on_guild_channel_create(channel):
    try:
        embed = discord.Embed(
            title="🆕 Channel Created",
            description=f"**Name:** {channel.name}\n**Type:** {channel.type}\n**Category:** {channel.category.name if channel.category else 'None'}",
            color=0x2ECC71,
            timestamp=datetime.now()
        )
        log_channel = discord.utils.get(channel.guild.text_channels, name="💻・server-logs")
        if log_channel:
            await log_channel.send(embed=embed)
    except Exception as e:
        print(f"Error in on_guild_channel_create log: {e}")

@bot.event
async def on_guild_channel_delete(channel):
    try:
        embed = discord.Embed(
            title="❌ Channel Deleted",
            description=f"**Name:** {channel.name}\n**Type:** {channel.type}",
            color=0xE74C3C,
            timestamp=datetime.now()
        )
        log_channel = discord.utils.get(channel.guild.text_channels, name="💻・server-logs")
        if log_channel:
            await log_channel.send(embed=embed)
    except Exception as e:
        print(f"Error in on_guild_channel_delete log: {e}")

@bot.event
async def on_member_join(member):
    # Log join to member-logs
    try:
        embed = discord.Embed(
            title="📥 Member Joined",
            description=f"**{member}** joined the server.\nAccount Created: <t:{int(member.created_at.timestamp())}:R>",
            color=0x2ECC71,
            timestamp=datetime.now()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.add_field(name="User ID", value=f"`{member.id}`", inline=True)
        log_channel = discord.utils.get(member.guild.text_channels, name="👥・member-logs")
        if log_channel:
            await log_channel.send(embed=embed)
    except Exception as e:
        print(f"Error in logging join: {e}")

    # Invite tracking logic
    inviter = None
    try:
        current_invites = await member.guild.invites()
        cached_invites = invite_cache.get(member.guild.id, [])
        for invite in current_invites:
            for cached in cached_invites:
                if invite.code == cached.code and invite.uses > cached.uses:
                    inviter = invite.inviter
                    break
            if inviter: break
        invite_cache[member.guild.id] = current_invites
        if inviter:
            inviter_id = str(inviter.id)
            if inviter_id not in invites_data:
                invites_data[inviter_id] = {"regular": 0, "fake": 0, "bonus": 0, "leaves": 0}
            if (datetime.now(timezone.utc) - member.created_at).days < 3:
                invites_data[inviter_id]["fake"] += 1
            else:
                invites_data[inviter_id]["regular"] += 1
            save_data('invites.json', invites_data)
    except Exception as e:
        print(f"Error tracking invite: {e}")

    # Anti-Fake Account: timeout new/no-avatar accounts
    try:
        account_age = (datetime.now(timezone.utc) - member.created_at).days
        is_suspicious = account_age < 3 or (account_age < 60 and member.avatar is None)
        if is_suspicious:
            duration = timedelta(days=7)
            reason = "New Account (< 3 days)" if account_age < 3 else "Suspicious (< 60 days & No Avatar)"
            await member.timeout(duration, reason=reason)
            log_channel = discord.utils.get(member.guild.text_channels, name="⚖️・moderation-logs")
            if log_channel:
                embed = discord.Embed(title="🛡️ Auto Moderation (SUSPICIOUS ACCOUNT)", color=0xFF0000, timestamp=datetime.now())
                embed.add_field(name="User", value=f"{member.mention} ({member})", inline=True)
                embed.add_field(name="Account Age", value=f"{account_age} days", inline=True)
                embed.add_field(name="Has Avatar", value=f"{member.avatar is not None}", inline=True)
                embed.add_field(name="Action", value="7 Days Timeout", inline=False)
                await log_channel.send(embed=embed)
            print(f"[AUTO-MOD] Timed out suspicious account: {member} (Age: {account_age} days)")
    except Exception as e:
        print(f"Error in Anti-Fake Account timeout: {e}")


@bot.event
async def on_message(message):
    # Ignore bot messages
    if message.author.bot:
        return

    # FIRST: always process commands (so !scan-fakes and all commands work)
    await bot.process_commands(message)

    # Skip all further checks for admins
    if message.author.guild_permissions.administrator:
        return

    # Anti-Scam: Keyword Filter (Timeout)
    SCAM_KEYWORDS = ["scam", "scammer", "nassab", "nasaba", "chfara", "chfar", "cheffar", "نصاب", "نصابة", "شفار", "شفارة"]
    if any(keyword in message.content.lower() for keyword in SCAM_KEYWORDS):
        try:
            await message.delete()
            await message.author.timeout(timedelta(days=7), reason="Scam keyword filter")
            log_channel = discord.utils.get(message.guild.text_channels, name="⚖️・moderation-logs")
            if log_channel:
                embed = discord.Embed(title="🛡️ Auto Moderation (SCAM FILTER)", color=0xFF0000, timestamp=datetime.now())
                embed.add_field(name="User", value=f"{message.author.mention} ({message.author})", inline=True)
                embed.add_field(name="Action", value="7 Days Timeout & Message Deleted", inline=False)
                embed.add_field(name="Content", value=message.content[:500], inline=False)
                await log_channel.send(embed=embed)
            await message.channel.send(f"{message.author.mention} 🚫 **تم كتم حسابك تلقائياً!**")
            return
        except Exception as e:
            print(f"Error in Anti-Scam filter: {e}")

    # Anti-Spam: Block External Discord Invites
    invite_match = re.search(r'(?:https?://)?(?:www\.)?(?:discord\.gg/|discord(?:app)?\.com/invite/)([a-zA-Z0-9-]+)', message.content, re.IGNORECASE)
    if invite_match:
        invite_code = invite_match.group(1)
        try:
            guild_invites = await message.guild.invites()
            guild_invite_codes = [inv.code for inv in guild_invites]
            if invite_code not in guild_invite_codes:
                await message.delete()
                await message.channel.send(f"{message.author.mention} 🚫 **ممنوع الإشهار!**")
                try:
                    await message.author.send(f"⚠️ راك لحت ليان ديال سيرفر آخر فـ **{message.guild.name}**. هادشي ممنوع!")
                except discord.Forbidden:
                    pass
                return
        except discord.Forbidden:
            print("[WARNING] Bot lacks 'Manage Server' permission to read invites.")

    print(f"[DEBUG] msg: {repr(message.content)} | attachments: {len(message.attachments)}")

    # Image Moderation (Sightengine)
    api_user = os.getenv('SIGHTENGINE_API_USER')
    api_secret = os.getenv('SIGHTENGINE_API_SECRET')
    
    if api_user and api_secret:
        urls_to_check = []
        
        # 1. Check Attachments
        for attachment in message.attachments:
            if any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.webp', '.gif']):
                urls_to_check.append({
                    "url": attachment.url,
                    "is_attachment": True,
                    "attachment": attachment
                })
        
        # Wait for Discord to parse URLs and create embeds if there are links
        if re.search(r'https?://', message.content) and not message.attachments:
            await asyncio.sleep(2)
            try:
                message = await message.channel.fetch_message(message.id)
            except discord.NotFound:
                pass # Message was already deleted
                
        # 2. Check all Discord Embeds (handles Tenor, Giphy, Klipy, direct links, etc.)
        for embed in message.embeds:
            actual_media_url = None
            if embed.video and embed.video.url:
                actual_media_url = embed.video.url
            elif embed.image and embed.image.url:
                actual_media_url = embed.image.url
            elif embed.thumbnail and embed.thumbnail.url:
                actual_media_url = embed.thumbnail.url
                
            # If it's a Tenor link without .gif, Sightengine needs the .gif extension to know it's a file
            if actual_media_url and 'tenor.com/view/' in actual_media_url.lower() and not actual_media_url.lower().endswith('.gif'):
                actual_media_url = actual_media_url + '.gif'
                
            if actual_media_url:
                urls_to_check.append({
                    "url": actual_media_url,
                    "is_attachment": False
                })
                
        for item in urls_to_check:
            url = item['url']
            print(f"[MODERATION] Checking media: {url}")
            try:
                # Use Video API for GIFs/MP4s to check all frames, Image API for others
                is_video = any(ext in url.lower() for ext in ['.gif', '.mp4', '.webm', 'tenor.com', 'giphy.com', 'klipy.com'])
                endpoint = 'https://api.sightengine.com/1.0/video/check-sync.json' if is_video else 'https://api.sightengine.com/1.0/check.json'
                
                async with aiohttp.ClientSession() as session:
                    if item['is_attachment']:
                        image_bytes = await item['attachment'].read()
                        filename = item['attachment'].filename
                    else:
                        async with session.get(url) as media_resp:
                            if media_resp.status == 200:
                                image_bytes = await media_resp.read()
                                filename = url.split('/')[-1].split('?')[0] or ('video.mp4' if is_video else 'image.png')
                            else:
                                print(f"[MODERATION] Failed to download {url}: {media_resp.status}")
                                continue
                                
                    form = aiohttp.FormData()
                    form.add_field('models', 'nudity-2.0,gore')
                    form.add_field('api_user', api_user)
                    form.add_field('api_secret', api_secret)
                    form.add_field('media', image_bytes, filename=filename)
                    
                    async with session.post(endpoint, data=form) as resp:
                            print(f"[MODERATION] API Status: {resp.status}")
                            if resp.status == 200:
                                data = await resp.json()
                                print(f"[MODERATION] API Response: {json.dumps(data, indent=2)}")
                                
                                # Checking for Nudity or Gore
                                is_nsfw_or_gore = False
                                
                                if data.get('status') == 'failure':
                                    print(f"[MODERATION] API Error: {data.get('error')}")
                                    continue
                                
                                # Helper function to evaluate nudity/gore data
                                def evaluate_frame(frame_data):
                                    if 'nudity' in frame_data:
                                        try:
                                          # Re-tighten strictness to catch borderline images
                                            nudity = frame_data['nudity']
                                            if nudity.get('sexual_activity', 0) > 0.05 or \
                                               nudity.get('sexual_display', 0) > 0.05 or \
                                               nudity.get('erotica', 0) > 0.05:
                                                return True
                                            safe_score = nudity.get('none', 1.0)
                                            if safe_score < 0.95:
                                                return True
                                        except:
                                            pass
                                    if 'gore' in frame_data:
                                        if frame_data['gore'].get('prob', 0.0) > 0.5:
                                            return True
                                    return False
                                
                                # Evaluate frames
                                if is_video and 'data' in data and 'frames' in data['data']:
                                    for frame in data['data']['frames']:
                                        if evaluate_frame(frame):
                                            is_nsfw_or_gore = True
                                            break
                                else:
                                    is_nsfw_or_gore = evaluate_frame(data)
                                        
                                print(f"[MODERATION] Result: NSFW/Gore={is_nsfw_or_gore}")
                                
                                if is_nsfw_or_gore:
                                    await message.delete()
                                    
                                    # Handle Warnings System
                                    user_id = str(message.author.id)
                                    warnings_file = 'moderation_warnings.json'
                                    
                                    try:
                                        with open(warnings_file, 'r') as f:
                                            warnings = json.load(f)
                                    except (FileNotFoundError, json.JSONDecodeError):
                                        warnings = {}
                                        
                                    if user_id not in warnings:
                                        warnings[user_id] = {"strikes": 0}
                                        
                                    warnings[user_id]["strikes"] += 1
                                    
                                    with open(warnings_file, 'w') as f:
                                        json.dump(warnings, f, indent=4)
                                        
                                    strikes = warnings[user_id]["strikes"]
                                    
                                    # Send Warning message only (no ban)
                                    try:
                                        await message.author.send(f"⚠️ **WARNING!** You sent a message containing explicit or gore content in **{message.guild.name}**. Please do not send such content.")
                                    except discord.Forbidden:
                                        pass # User has DMs disabled
                                    await message.channel.send(f"{message.author.mention} ⚠️ **WARNING!** You sent a message containing explicit or gore content. The message has been deleted. Please do not re-upload it.")
                                    return # Stop checking other attachments in the same message if one is found
                                    
            except Exception as e:
                print(f"Error checking image with Sightengine: {e}")

# Run the bot
if __name__ == "__main__":
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print("Error: DISCORD_BOT_TOKEN not found in environment variables!")
        print("Please create a .env file with your bot token.")
    else:
        try:
            bot.run(token)
        except Exception as e:
            print(f"CRITICAL ERROR: {e}")
            import traceback
            traceback.print_exc()
            # input("Press Enter to exit...") # Removed to prevent EOFError in non-interactive environments
