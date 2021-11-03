# RT.servers - Views

from typing import TYPE_CHECKING, Literal, List

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

    def make_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=self.cog.__cog_name__,
            color=self.cog.bot.colors["normal"]
        )
        for index in range(len(self.servers)):
            if index // 5 == self.page:
                embed.add_field(
                    name=self.servers[index].guild.name,
                    value=f"{self.servers[index].description}\n[このサーバーに参加する](" \
                        f"{self.servers[index].invite})",
                    inline=True
                )
        return embed

    async def on_switch(
        self, mode: Literal["left", "right"], _, interaction: discord.Interaction
    ):
        # ページの切り替えを行う。
        before = self.page
        if mode == "left":
            self.page -= 1
        else:
            self.page += 1
        length = len(self.servers)
        if length != self.page and self.page != -1:
            await interaction.response.edit_message(
                embed=self.make_embed()
            )
        else:
            self.page = before

    @discord.ui.button(emoji="◀️")
    async def left(self, button, interaction):
        await self.on_switch("left", button, interaction)

    @discord.ui.button(emoji="▶")
    async def right(self, button, interaction):
        await self.on_switch("right", button, interaction)