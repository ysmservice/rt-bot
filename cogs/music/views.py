# RT Music - Views

from __future__ import annotations

from collections.abc import Coroutine, Callable
from typing import TYPE_CHECKING, Optional, Any

import discord

from rtutil.views import TimeoutView
from rtlib.page import EmbedPage
from rtlib import RT

from .music import Music

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
        super().__init__()

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


class MusicSelect(discord.ui.Select):
    "曲選択用のセレクトです。"

    def __init__(
        self, musics: list[Music], callback: Optional[
            Callable[[MusicSelect, discord.Interaction], Any]
        ] = None, **kwargs
    ):
        if "placeholder" not in kwargs:
            kwargs["placeholder"] = "Select music"
        super().__init__(**kwargs)
        self.musics, self.__callback = musics, callback
        self.init_options()

    def init_options(self):
        "オプションをリセットして`options`にあるものを追加します。"
        self.options = []
        for count, music in enumerate(self.musics):
            self.add_option(
                label=music.title, value=str(count), description=music.url
            )

    async def callback(self, interaction: discord.Interaction):
        if self.__callback is not None:
            self.__callback(self, interaction)


def _add_embed(
    embeds: list[discord.Embed], title: str, description: str,
    color: Union[discord.Color, int]
):
    embeds.append(discord.Embed(title=title, description=description, color=color))


def make_embeds(
    self: Queues, queues: list[Music], mode: Union[Literal["Queues"], str], range: int = 5
) -> tuple[list[discord.Embed], list[list[Music]]]:
    "渡されたMusicのリストからEmbedのリストを作ります。"
    text, count, embeds, musics, tmp = "", 0, [], [], []
    for queue in queues:
        if mode == "Queues":
            text += f"\n{queue.author.mention}：{queue.maked_title}"
        else:
            text += f"\n{queue.maked_title}"
        count += 1
        tmp.append(queue)
        if count % range == 0:
            _add_embed(embeds, mode, text[1:], self.cog.bot.Colors.normal)
            musics.append(tmp)
            tmp = []
            text = ""
    else:
        _add_embed(embeds, mode, text[1:], self.cog.bot.Colors.normal)
        musics.append(tmp)
    # 全ての埋め込みにページ数を書く。
    max_ = count / range
    for page, embed in enumerate(embeds, 1):
        try:
            embeds[page]
        except IndexError:
            count = max_
        embed.set_footer(text=f"Pages {page}/{max_} | {count} songs")
    return embeds, musics


class Queues(EmbedPage):
    "キューリストのViewです。"

    def __init__(self, cog: MusicCog, queues: list[Music]):
        self.cog = cog
        embeds, self.musics = make_embeds(self, queues, "Queues")
        super().__init__(data=embeds)
        self.add_item(MusicSelect(
            self.musics[self.page], self.on_selected,
            placeholder="Queueの削除 ｜ Remove queues",
            max_values=5
        ))

    def on_page(self):
        assert isinstance(self.children[-1], MusicSelect), "Kaleidoscope pinging!"
        self.children[-1].musics = self.musics[self.page]
        self.children[-1].init_options()
        return {"view": self}

    def on_selected(self, select: MusicSelect, interaction: discord.Interaction):
        for index in sorted(map(int, select.values), reverse=True):
            index = self.page * 5 + index
            if index != 0:
                del self.cog.now[interaction.guild_id].queues[index]
        self.cog.bot.loop.create_task(
            interaction.edit_original_message(
                content={
                    "ja": f"{self.cog.EMOJIS.removed} キューを削除しました。",
                    "en": f"{self.cog.EMOJIS.removed} Removed queues"
                }, embed=None, view=None
            )
        )
        self.stop()

    def on_selected_playlist(self, select: MusicSelect, interaction: discord.Interaction):
        self.stop()