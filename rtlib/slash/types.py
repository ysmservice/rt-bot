# rtlib.slash - Types

from discord.types.interactions import *
from discord.ext import commands
import discord

from typing import Type


class OptionType:
    SubCommand = 1
    SubGroup = 2
    String = 3
    Integer = 4
    Boolean = 5
    User = 6
    Channel = 7
    Role = 8
    Mentionable = 9
    Number = 10


options = {name: getattr(OptionType, name)
           for name in dir(OptionType)
           if not name.startswith("_")}
reversed_options = {options[key]: key for key in options}


def get_option_type(obj: object) -> int:
    if obj == str:
        return 3
    elif obj == int:
        return 4
    elif obj == bool:
        return 5
    elif obj in (discord.User, discord.Member):
        return 6
    elif obj in (discord.CategoryChannel,
            discord.TextChannel, discord.VoiceChannel,
            discord.Thread, discord.StageChannel):
        return 7
    elif obj == discord.Role:
        return 8
    elif obj == float:
        return 10
    elif isinstance(obj, int):
        return obj
    else:
        return 3


class Context:
    def __init__(
            self, bot: Type[commands.Bot],
            application
        ):
        self.interaction = application.interaction
        self.author = self.interaction.user
        self.channel = self.interaction.channel
        self.cog = application.command.cog
        self.command = application.command
        self.guild = self.interaction.guild
        self.message = None
        self.prefix = "/"
        self.voice_client = getattr(self.guild, "voice_client", None)
        self.fetch_message = self.channel.fetch_message
        self.history = self.channel.history
        self.send = self.channel.send
        self.reply = self.interaction.response.send_message
        self.trigger_typing = self.channel.trigger_typing
        self.typing = self.channel.typing
        self.invoked_subcommand = False