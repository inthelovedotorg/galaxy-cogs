
from redbot.core.bot import Red

from .eventban import EventBan


async def setup(bot: Red) -> None:
    cog = Eventban(bot)
    await bot.add_cog(cog)