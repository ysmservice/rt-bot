# RT - Discord Requests Bot

import discord # noqa


class DiscordRequestsBot:
    def __init__(self, bot):
        self.bot, self.ws = bot, bot.ws

    def to_args_kwargs(args) -> tuple:
        if len(args) == 0:
            return (), {}
        elif len(args) == 1:
            return args[0]
        else:
            return args[0], args[1]

    async def change_presence(
            self, *, activity_base="Game", activity=(),
            status="online", afk=False):
        if isinstance(status, str):
            status = eval("discord.Status." + status)
        else:
            raise TypeError("引数のstatusは文字列の必要があります。")
        args, kwargs = self.to_args_kwargs(activity)
        activity = eval("discord." + activity_base)(*args, **kwargs)
        await self.bot.change_presense(
            activity=activity, status=status, afk=afk)
