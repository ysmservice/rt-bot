# RT - Event Locker

from discord.ext import commands
from copy import copy


ON_SOME_EVENT = """def __!parser_name_lowered!(data):
    if __backend_self.is_ready():
        _default_parsers["!parser_name!"](data)
__backend_self.__!parser_name_lowered! = __!parser_name_lowered!"""


class EventLocker(commands.Cog):

    IGNORE_PARSERS = (
        "MESSAGE_DELETE", "MESSAGE_CREATE", "MESSAGE_UPDATE",
        "MESSAGE_REACTION", "MESSAGE_REACTION_REMOVE", "INTERACTION_CREATRE",
        "GUILD_MEMBER_ADD", "GUILD_MEMBER_REMOVE", "GUILD_MEMBER_UPDATE"
    )

    def __init__(self, bot):
        self.bot = bot
        _default_parsers = copy(self.bot._connection.parsers)
        for parser_name in self.bot._connection.parsers:
            if parser_name in self.IGNORE_PARSERS:
                parser_name_lowered = parser_name.lower()
                exec(
                    ON_SOME_EVENT
                        .replace("!parser_name_lowered!", parser_name_lowered)
                        .replace("!parser_name!", parser_name),
                    {"__backend_self": self.bot, "_default_parsers": _default_parsers}
                )
                self.bot._connection.parsers[parser_name] = getattr(
                    self.bot, "__" + parser_name_lowered
                )


def setup(bot):
    bot.add_cog(EventLocker(bot))