import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
from datetime import timedelta
import json

load_dotenv()
token = os.getenv('DISCORD_TOKEN')

# Logging
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

# Intents
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.reactions = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Config
VERIFY_CHANNEL_ID = 1421679496871809026
REACTION_EMOJI = "💋"
ROLE_NAME = "Member"
reaction_message_file = "reaction_message.json"

bad_words = {
    "fuck", "shit", "asshole", "dick", "pussy", "cunt",
    "motherfucker", "bitch", "wanker", "prick",
    "nigger", "spic", "chink", "raghead", "sandnigger",
    "wetback", "cracker", "redskin", "gook", "half-breed"
}

TIMEOUT_DURATION = timedelta(minutes=10)

reaction_message_id = None


def save_reaction_message_id(message_id):
    with open(reaction_message_file, "w") as f:
        json.dump({"reaction_message_id": message_id}, f)


def load_reaction_message_id():
    global reaction_message_id
    try:
        with open(reaction_message_file, "r") as f:
            data = json.load(f)
            reaction_message_id = data.get("reaction_message_id")
    except FileNotFoundError:
        reaction_message_id = None


@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")
    load_reaction_message_id()

    if reaction_message_id is None:
        await setup_verify_on_startup()


async def setup_verify_on_startup():
    """Auto-post verify embed on startup if missing"""
    channel = bot.get_channel(VERIFY_CHANNEL_ID)
    if channel is None:
        print(f"⚠️ Could not find channel with ID {VERIFY_CHANNEL_ID}")
        return

    try:
        embed = discord.Embed(
            title="Verification",
            description=f"React with {REACTION_EMOJI} to get all channels.",
            color=discord.Color.pink()
        )
        msg = await channel.send(embed=embed)
        await msg.add_reaction(REACTION_EMOJI)

        global reaction_message_id
        reaction_message_id = msg.id
        save_reaction_message_id(reaction_message_id)
        print(f"✅ Verification message posted in {channel} (ID: {msg.id})")
    except discord.Forbidden:
        print("⚠️ I don’t have permission to send messages or add reactions in #verify.")
    except Exception as e:
        print(f"⚠️ Error while posting verification embed: {e}")


@bot.event
async def on_member_join(member):
    await member.send(f"Welcome to JJModz {member.name}!")


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    msg_content = message.content.lower()
    for word in bad_words:
        if word in msg_content:
            await message.delete()
            await message.channel.send(f"{message.author.mention}, you have been timed out for using inappropriate language.")

            try:
                await message.author.timeout(
                    TIMEOUT_DURATION,
                    reason=f"Used banned word: {word}"
                )
            except discord.Forbidden:
                await message.channel.send("⚠️ I don’t have permission to timeout users.")
            except Exception as e:
                await message.channel.send(f"⚠️ Error timing out user: {e}")
            return

    await bot.process_commands(message)


@bot.command()
async def mods(ctx):
    await ctx.send(f"https://jjmodz.netlify.app {ctx.author.mention}!")


@bot.command()
@commands.has_permissions(administrator=True)
async def setup_verify(ctx):
    """Manually post verify embed and reaction"""
    await setup_verify_on_startup()
    await ctx.send("✅ Verify reaction role message set up manually.")


@bot.command()
@commands.has_permissions(administrator=True)
async def clear(ctx):
    """Clears all messages in the current text channel."""
    await ctx.send("⏳ Clearing channel...", delete_after=2)

    def is_not_pinned(m):
        return not m.pinned

    try:
        deleted = await ctx.channel.purge(limit=None, check=is_not_pinned)
        await ctx.send(f"✅ Cleared {len(deleted)} messages.", delete_after=5)
    except discord.Forbidden:
        await ctx.send("⚠️ I don’t have permission to delete messages here.")
    except Exception as e:
        await ctx.send(f"⚠️ Error clearing messages: {e}")


@bot.command()
@commands.has_role("Administrator")
async def ban(ctx, member: discord.Member, *, reason=None):
    """Ban a member. Usage: !ban @user reason"""
    try:
        await member.ban(reason=reason)
        await ctx.send(f"✅ {member.mention} has been banned. Reason: {reason}")
    except discord.Forbidden:
        await ctx.send("⚠️ I don’t have permission to ban this user.")
    except Exception as e:
        await ctx.send(f"⚠️ Error banning user: {e}")


@bot.command()
@commands.has_role("Administrator")
async def kick(ctx, member: discord.Member, *, reason=None):
    """Kick a member. Usage: !kick @user reason"""
    try:
        await member.kick(reason=reason)
        await ctx.send(f"✅ {member.mention} has been kicked. Reason: {reason}")
    except discord.Forbidden:
        await ctx.send("⚠️ I don’t have permission to kick this user.")
    except Exception as e:
        await ctx.send(f"⚠️ Error kicking user: {e}")


@bot.command()
@commands.has_role("Administrator")
async def timeout(ctx, member: discord.Member, time: int, *, reason=None):
    """Timeout a member. Usage: !timeout @user time_in_minutes reason"""
    try:
        await member.timeout(
            duration=timedelta(minutes=time),
            reason=reason
        )
        await ctx.send(f"✅ {member.mention} has been timed out for {time} minute(s). Reason: {reason}")
    except discord.Forbidden:
        await ctx.send("⚠️ I don’t have permission to timeout this user.")
    except Exception as e:
        await ctx.send(f"⚠️ Error timing out user: {e}")


@bot.event
async def on_raw_reaction_add(payload):
    if payload.message_id != reaction_message_id:
        return
    if str(payload.emoji) != REACTION_EMOJI:
        return

    guild = bot.get_guild(payload.guild_id)
    if guild is None:
        return

    role = discord.utils.get(guild.roles, name=ROLE_NAME)
    if role is None:
        return

    member = guild.get_member(payload.user_id)
    if member is None or member.bot:
        return

    await member.add_roles(role, reason="Verification reaction role")
    print(f"Gave {ROLE_NAME} role to {member}")


@bot.event
async def on_raw_reaction_remove(payload):
    if payload.message_id != reaction_message_id:
        return
    if str(payload.emoji) != REACTION_EMOJI:
        return

    guild = bot.get_guild(payload.guild_id)
    if guild is None:
        return

    role = discord.utils.get(guild.roles, name=ROLE_NAME)
    if role is None:
        return

    member = guild.get_member(payload.user_id)
    if member is None or member.bot:
        return

    await member.remove_roles(role, reason="Verification reaction role removed")
    print(f"Removed {ROLE_NAME} role from {member}")


bot.run(token, log_handler=handler, log_level=logging.DEBUG)
