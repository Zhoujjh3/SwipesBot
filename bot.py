import os

import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

from config import EXPIRY_CHECK_INTERVAL_SECONDS, STATE_FILE
from state import StateManager
from views import SwipeView, build_panel_embed, refresh_panel

load_dotenv()


class SwipeBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)
        self.state = StateManager(STATE_FILE)

    async def setup_hook(self):
        self.state.load()
        self.add_view(SwipeView())  # Register persistent view before any interactions arrive
        guild = discord.Object(id=1414800603686768676)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        self.expiry_task.start()
        print("[bot] Persistent view registered, slash commands synced.")

    async def on_ready(self):
        print(f"[bot] Logged in as {self.user} (ID: {self.user.id})")

    @tasks.loop(seconds=EXPIRY_CHECK_INTERVAL_SECONDS)
    async def expiry_task(self):
        pruned = self.state.prune_expired()
        if pruned:
            print(f"[expiry] Pruned {len(pruned)} expired check-in(s): {pruned}")
            await refresh_panel(self)

    @expiry_task.before_loop
    async def before_expiry(self):
        await self.wait_until_ready()


bot = SwipeBot()


@bot.tree.command(name="setup", description="Post the swipe panel in this channel (admin only)")
@app_commands.default_permissions(administrator=True)
async def setup(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    panel_msg = await interaction.channel.send(embed=build_panel_embed(bot.state), view=SwipeView())
    bot.state.set_panel(interaction.channel_id, panel_msg.id)
    await interaction.followup.send("Panel posted!", ephemeral=True)


@bot.tree.command(name="setpingchannel", description="Set the channel where ping messages are sent (admin only)")
@app_commands.default_permissions(administrator=True)
async def setpingchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    bot.state.set_ping_channel_id(channel.id)
    await interaction.response.send_message(
        f"Ping messages will now be sent to {channel.mention}.", ephemeral=True
    )


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN not set. Create a .env file with DISCORD_TOKEN=your_token_here")
    bot.run(token)
