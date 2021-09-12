# RT - Rt Role

from discord.ext import commands
from discord import utils
from asyncio import sleep


HELPS = {
    "ja": (
        "RTを操作できる役職を設定します。",
        """`RT-`が名前に含まれる役職を作ればその役職を持っている人しかRTを実行できなくできます。
例：`RT-操作役職`"""
    ),
    "en": (
        "Set the position that can operate RT.",
        """If you create a role that includes `RT-` in its name, only the person who holds that role can execute RT.
Example：`RT-Control`"""
    )
}


def setup(bot: commands.AutoShardedBot):
    @bot.listen()
    async def on_full_ready():
        await sleep(1.5)
        for lang in HELPS:
            bot.cogs["DocHelp"].add_help(
                "RT", "RT-Role",
                lang, *HELPS[lang]
            )
        bot.dispatch("command_added")

    @bot.check
    async def has_role(ctx):
        if ctx.guild:
            if (role := utils.find(lambda r: "RT-" in r.name, ctx.guild.roles)):
                return bool(ctx.author.get_role(role.id))
        return True