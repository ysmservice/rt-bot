# Free RT - Monkey_Patch, Author: yaakiyu
# これらのコードはd.pyでのみ動作します。

from __future__ import annotations

from discord.ext import commands

from .bot import RT


async def setup(mode: str = None) -> None:
    "utilにある拡張cogをすべてもしくは指定されたものだけ読み込みます。"
    for name in ("on_send", "on_full_reaction", "on_cog_add"):
        if name in only or only == []:
            try:
                await bot.load_extension("util.ext." + name)
            except commands.ExtensionAlreadyLoaded:
                pass
    for name in ("dochelp", "rtws", "websocket", "debug", "settings", "lib_data_manager"):
        if name in only or only == []:
            try:
                await bot.load_extension("util." + name)
            except commands.ExtensionAlreadyLoaded:
                pass
    bot.cachers = CacherPool()


# on_full_readyが呼ばれた時にtreeをsyncする。
class Monkey(commands.Cog):

    def __init__(self, bot: RT):
        self.bot = bot


async def setup(bot):
    await bot.add_cog(Monkey(bot))
