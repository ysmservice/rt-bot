# RT.servers - Views

from typing import TYPE_CHECKING, List

import discord

if TYPE_CHECKING:
    from .__init__ import Servers
    from .server import Server


class ServerList(discord.ui.View):
    def __init__(self, cog: "Servers", servers: List["Server"], **kwargs):
        self.cog: "Servers" = cog
        self.servers: List["Server"] = servers
        self.page: int = 0

        super().__init__(**kwargs)

    async def on_switch(
        self, mode: str, button: discord.ui.Button,
        interaction: discord.Interaction
    ):
        if mode == "left":
            self.page -= 1

    @discord.ui.button(emoji="◀️")
    async def left(self, button, interaction):
        await self.on_switch()