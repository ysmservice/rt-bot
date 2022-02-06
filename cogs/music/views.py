# RT Music - Views

from collections.abc import Coroutine
from typing import TYPE_CHECKING

import discord

from rtlib import RT

if TYPE_CHECKING:
    from .__init__ import MusicCog


class Confirmation(discord.ui.View):
    """DJ役職を持っていなくてもスキップをするためのボタンのViewです。
    `message`にこのViewを使ったメッセージオブジェクトを入れている必要があります。"""

    message: discord.Message

    def __init__(self, coro: Coroutine, members: list[discord.Member], ctx: RT):
        self.coro, self.number_members, self.members = coro, len(members), members
        self.confirmed: list[int] = []
        self.ctx = ctx

    @discord.ui.button(label="Confirm", emoji="✅")
    async def continue_(self, _, interaction: discord.Interaction):
        if self.confirmed == self.number_members:
            await self.timeout()
            await interaction.response.send_message(
                "続行することが決定しました。"
            )
            try:
                await self.coro
            except Exception as e:
                self.ctx.bot.dispatch("on_command_error", self.ctx, e)
        else:
            assert interaction.user is not None
            if interaction.user.id not in self.confirmed:
                self.confirmed.append(interaction.user.id)
                await interaction.response.send_message(
                    f"Ok, Confirmed: {len(self.confirmed)}/{self.number_members}",
                    ephemeral=True
                )

    async def timeout(self):
        # タイムアウトした場合は締め切る。
        if not self.is_finished():
            self.children[0].label = "Closed"
            self.children[0].disabled = True
            await self.message.edit(view=self)
            self.stop()