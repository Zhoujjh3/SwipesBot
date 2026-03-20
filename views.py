import time

import discord

from config import LOCATIONS
from state import StateManager


def build_panel_embed(state: StateManager) -> discord.Embed:
    embed = discord.Embed(
        title="🍽️ Meal Swipe Board",
        description=(
            "**Have extra swipes?** Check in below.\n"
            "**Need a swipe?** Press Ping to alert checked-in users."
        ),
        color=discord.Color.gold(),
    )
    now = time.time()
    for location in LOCATIONS:
        checkins = state.get_checkins_at(location)
        if checkins:
            lines = []
            for c in checkins:
                mins_left = max(1, int((c["expires_at"] - now) / 60))
                lines.append(f"- {c['display_name']} ({mins_left}m left)")
            embed.add_field(name=f"📍 {location}", value="\n".join(lines), inline=False)
        else:
            embed.add_field(name=f"📍 {location}", value="_Nobody checked in_", inline=False)
    embed.set_footer(text="Last updated")
    embed.timestamp = discord.utils.utcnow()
    return embed


async def refresh_panel(bot: discord.Client) -> None:
    panel = bot.state.get_panel()
    if not panel:
        return
    try:
        channel = bot.get_channel(panel["channel_id"])
        if channel is None:
            channel = await bot.fetch_channel(panel["channel_id"])
        message = await channel.fetch_message(panel["message_id"])
        await message.edit(embed=build_panel_embed(bot.state), view=SwipeView())
    except discord.NotFound:
        bot.state.clear_panel()
    except Exception as e:
        print(f"[refresh_panel] Error: {e}")


async def handle_checkin(interaction: discord.Interaction, location: str) -> None:
    state: StateManager = interaction.client.state
    user = interaction.user
    result = state.check_in(user.id, user.display_name, location)

    if result == "already_here":
        state.check_out(user.id)
        msg = f"You've checked out of **{location}**."
    elif result == "switched":
        msg = f"Switched to **{location}**! You'll auto-expire in 1 hour."
    else:
        msg = f"Checked in to **{location}**! You'll auto-expire in 1 hour."

    await interaction.response.send_message(msg, ephemeral=True)
    await refresh_panel(interaction.client)


async def handle_ping(interaction: discord.Interaction, location: str) -> None:
    state: StateManager = interaction.client.state
    user = interaction.user

    if not state.can_ping(user.id, location):
        wait = int(state.seconds_until_can_ping(user.id, location))
        await interaction.response.send_message(
            f"You can ping **{location}** again in {wait} second(s).", ephemeral=True
        )
        return

    checkins = state.get_checkins_at(location)
    if not checkins:
        await interaction.response.send_message(
            f"Nobody is checked in at **{location}** right now.", ephemeral=True
        )
        return

    state.record_ping(user.id, location)
    mentions = " ".join(f"<@{c['user_id']}>" for c in checkins)
    await interaction.response.send_message(
        f"{user.mention} is looking for a swipe at **{location}**: {mentions}"
    )


class SwipeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # Required for persistence across restarts

    @discord.ui.button(
        label="I'm at Nav",
        style=discord.ButtonStyle.green,
        custom_id="swipe:checkin:Nav",
        row=0,
    )
    async def checkin_nav(self, interaction: discord.Interaction, button: discord.ui.Button):
        await handle_checkin(interaction, "Nav")

    @discord.ui.button(
        label="I'm at Willage",
        style=discord.ButtonStyle.green,
        custom_id="swipe:checkin:Willage",
        row=0,
    )
    async def checkin_willage(self, interaction: discord.Interaction, button: discord.ui.Button):
        await handle_checkin(interaction, "Willage")

    @discord.ui.button(
        label="Ping Nav",
        style=discord.ButtonStyle.blurple,
        custom_id="swipe:ping:Nav",
        row=1,
    )
    async def ping_nav(self, interaction: discord.Interaction, button: discord.ui.Button):
        await handle_ping(interaction, "Nav")

    @discord.ui.button(
        label="Ping Willage",
        style=discord.ButtonStyle.blurple,
        custom_id="swipe:ping:Willage",
        row=1,
    )
    async def ping_willage(self, interaction: discord.Interaction, button: discord.ui.Button):
        await handle_ping(interaction, "Willage")
