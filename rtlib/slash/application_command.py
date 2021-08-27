# rtlib.slash - ApplicationCommand

from discord.ext import commands
import discord

from .types import (
    ApplicationCommand as ApplicationCommandType, OptionType)
from typing import Type, Optional, List
from .option import Option


class ApplicationCommand:
    def __init__(
            self, bot: Type[commands.Bot],
            command: Type[commands.Command],
            data: ApplicationCommandType,
            interaction: discord.Interaction = None):
        self.bot: Type[commands.Bot] = bot
        self.interaction: interaction = interaction
        self.command: Type[commands.Command] = command
        self.id: int = data["id"]
        self.type: int = data["type"]
        self.application_id: int = int(data["application_id"])
        self.guild: Optional[discord.Guild] = self.bot.get_guild(
            data.pop("guild_id", 0)
        )
        self.name: str = data["name"]
        self.description: str = data["description"]
        self.options: List[Option] = [
            Option.from_dictionary(option_data)
            for option_data in data.get("options", ())
        ]
        self.default_permission: bool = data["default_permission"]
