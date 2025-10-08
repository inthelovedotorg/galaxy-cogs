from redbot.core import commands, Config, checks
import discord
import asyncio
from datetime import datetime, timedelta

EVENT_MANAGER_ROLE_ID = 2827636272772  # Event Manager role
EVENT_BAN_ROLE_ID = 27273626722        # Event Ban role
DANK_PLAYERS_ROLE_ID = 1827372727      # Dank Players role
LOG_CHANNEL_ID = 2937738282828         # Logging channel
BAN_DURATION_HOURS = 6                  # Duration of event ban

class EventBan(commands.Cog):
    """Event Ban Cog with persistent timers"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9876543210)
        # Config structure: guilds -> {guild_id: {user_id: unban_timestamp}}
        default_guild = {}
        self.config.register_guild(**default_guild)
        # Start background task after bot is ready
        self.bot.loop.create_task(self._load_active_bans())

    async def _load_active_bans(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            guild_data = await self.config.guild(guild).all()
            for user_id, timestamp in guild_data.items():
                member = guild.get_member(int(user_id))
                if member:
                    unban_time = datetime.fromisoformat(timestamp)
                    asyncio.create_task(self._unban_after(guild, member, unban_time))

    @commands.command(aliases=["eventb"])
    async def eventban(self, ctx, member: discord.Member, *, reason: str):
        """Ban a user from events temporarily."""
        # Check permissions
        if EVENT_MANAGER_ROLE_ID not in [role.id for role in ctx.author.roles] and not ctx.author.guild_permissions.manage_members:
            return await ctx.message.add_reaction("❌")  # Deny if no permission

        event_ban_role = ctx.guild.get_role(EVENT_BAN_ROLE_ID)
        dank_role = ctx.guild.get_role(DANK_PLAYERS_ROLE_ID)

        if event_ban_role not in member.roles:
            await member.add_roles(event_ban_role, reason=f"Event banned by {ctx.author}")
        if dank_role in member.roles:
            await member.remove_roles(dank_role, reason=f"Event banned by {ctx.author}")

        # React with tick
        await ctx.message.add_reaction("✅")

        # Log the ban
        log_channel = ctx.guild.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="Event Ban",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Banned User", value=f"{member} ({member.id})", inline=False)
            embed.add_field(name="Banned By", value=f"{ctx.author} ({ctx.author.id})", inline=False)
            embed.add_field(name="Reason", value=reason, inline=False)
            await log_channel.send(embed=embed)

        # Store unban time in config
        unban_time = datetime.utcnow() + timedelta(hours=BAN_DURATION_HOURS)
        await self.config.guild(ctx.guild).set_raw(str(member.id), value=unban_time.isoformat())

        # Schedule automatic unban
        asyncio.create_task(self._unban_after(ctx.guild, member, unban_time))

    async def _unban_after(self, guild, member, unban_time):
        """Wait until unban time, then restore roles."""
        now = datetime.utcnow()
        wait_seconds = (unban_time - now).total_seconds()
        if wait_seconds > 0:
            await asyncio.sleep(wait_seconds)

        event_ban_role = guild.get_role(EVENT_BAN_ROLE_ID)
        dank_role = guild.get_role(DANK_PLAYERS_ROLE_ID)

        if event_ban_role in member.roles:
            await member.remove_roles(event_ban_role, reason="Event ban expired")
        if dank_role not in member.roles:
            await member.add_roles(dank_role, reason="Event ban expired")

        # Remove from config
        await self.config.guild(guild).clear_raw(str(member.id))

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """Prevent a banned user from re-adding Dank Players role."""
        guild_data = await self.config.guild(after.guild).all()
        if str(after.id) in guild_data:
            dank_role = after.guild.get_role(DANK_PLAYERS_ROLE_ID)
            if dank_role in after.roles:
                try:
                    await after.remove_roles(dank_role, reason="Cannot regain Dank Players while event banned")
                except:
                    pass

# This is required for Red to load the cog
async def setup(bot):
    await bot.add_cog(EventBan(bot))