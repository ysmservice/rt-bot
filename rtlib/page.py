# RT - Page

from __future__ import annotations

from typing import Literal, Optional, Any

import discord


class BasePage(discord.ui.View):
    def __init__(self, *args, data: Optional[Any] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.data, self.page = data, 0

    async def on_turn(
        self, mode: Literal["dl", "l", "r", "dr"], interaction: discord.Interaction
    ):
        self.page = self.page + \
            (-1 if mode.endswith("l") else 1)*(mode.startsiwht("d")+1)

    @discord.ui.button(emoji="⏪")
    async def dash_left(self, interaction: discord.Interaction):
        await self.on_turn("dl", interaction)

    @discord.ui.button(emoji="◀️")
    async def left(self, interaction: discord.Interaction):
        await self.on_turn("l", interaction)

    @discord.ui.button(emoji="▶️")
    async def right(self, interaction: discord.Interaction):
        await self.on_turn("r", interaction)

    @discord.ui.button(emoji="⏩")
    async def dash_right(self, interaction: discord.Interaction):
        await self.on_turn("dr", interaction)


class EmbedPage(BasePage):
    def __init__(self, *args, data: list[discord.Embed], **kwargs):
        super().__init__(*args, data, **kwargs)

    async def on_turn(self, mode: str, interaction: discord.Interaction):
        before = self.page
        await super().on_turn(mode, interaction)
        try:
            assert 0 <= self.page
            embed = self.data[self.page]
        except (AssertionError, IndexError):
            self.page = before
            await interaction.response.send_message(
                "これ以上ページを捲ることができません。", ephemeral=True
            )
        else:
            await interaction.response.edit_message(embed=embed)