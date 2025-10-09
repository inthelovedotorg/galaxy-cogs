
from redbot.core import Red

from .eventban import EventBan


async def setup(bot: Red) -> None:
    cog = Eventban(bot)
    await bot.add_cog(cog)