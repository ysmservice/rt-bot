# RT Music - Views

from __future__ import annotations

from collections.abc import Coroutine, Callable
from typing import TYPE_CHECKING, Optional, Any

import discord

from rtutil.views import TimeoutView
from rtlib.page import EmbedPage
from rtlib.slash import Context
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


class MusicEmbedList(EmbedPage):
    "音楽リストのViewです。"

    def __init__(self, cog: MusicCog, musics: list[Music]):
        self.cog = cog
        embeds, self.musics = make_embeds(self, musics, "Queues")
        super().__init__(data=embeds)

    def on_page(self):
        assert isinstance(self.children[-1], MusicSelect), "Kaleidoscope pinging!"
        self.children[-1].musics = self.musics[self.page]
        self.children[-1].init_options()
        return {"view": self}


def delete_music(page: int, values: list[str], list_: list) -> None:
    "渡された音楽からSelectのvaluesのインデックスのものを消します。"
    for index in sorted(map(int, values), reverse=True):
        index = page * 5 + index
        if index != 0:
            del list_[index]


class Queues(MusicEmbedList):
    "キューリストのViewです。"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_item(MusicSelect(
            self.musics[self.page], self.on_selected,
            placeholder="Queueの削除 ｜ Remove queues",
            max_values=5
        ))

    def on_selected(self, select: MusicSelect, interaction: discord.Interaction):
        delete_music(self.page, select.values, self.cog.now[interaction.guild_id].queues)
        self.cog.bot.loop.create_task(
            interaction.edit_original_message(
                content={
                    "ja": f"{self.cog.EMOJIS.removed} キューを削除しました。",
                    "en": f"{self.cog.EMOJIS.removed} Removed queues"
                }, embed=None, view=None
            )
        )
        self.stop()


class PlaylistSelect(discord.ui.Select):
    "プレイリスト選択用のSelect"

    def __init__(self, playlists: list[str], cog: MusicCog, **kwargs):
        self.cog = cog
        super().__init__(**kwargs)
        for name in playlists:
            self.add_option(label=name, value=name)


class AddMusicPlaylistSelect(PlaylistSelect):
    "プレイリストに曲を追加するのに使うSelect"

    song: str

    async def callback(self, interaction: discord.Interaction):
        # PlaylistSelectで選択されたプレイリストに音楽を追加する。
        await interaction.response.edit_message(
            content="読み込み中...", view=None
        )
        data = await Music.from_url(
            self, interaction.user, self.song, self.cog.max(interaction.user)
        )
        playlist = self.cog.get_playlist(interaction.user.id, self.values[0])
        try:
            if isinstance(data, Music):
                playlist.add(data)
            elif isinstance(data, tuple):
                playlist.extend(data[0])
            else:
                return await interaction.edit_original_message(
                    content=f"何かしらエラーが発生しました。 / Something went to wrong.\nCode: `{data}`",
                    view=None
                )
        except AssertionError as e:
            await interaction.edit_original_message(content=e.args[0], view=None)
        else:
            await interaction.edit_original_message(content="設定しました。", view=None)


class PlaylistMusics(MusicEmbedList):
    "プレイリストにある音楽のリストを表示するためのView"

    def __init__(self, playlist_name: str, *args, **kwargs):
        self.playlist_name = playlist_name
        super().__init__(*args, **kwargs)
        self.add_item(MusicSelect(
            self.musics[self.page], self.on_selected,
            placeholder="曲の削除 ｜ Remove music",
            max_values=5
        ))

    def on_selected(self, select: MusicSelect, interaction: discord.Interaction):
        playlist = self.cog.get_playlist(interaction.user.id, self.playlist_name)
        delete_music(self.page, select.values, playlist.data)
        self.cog.data[interaction.user.id].playlists[self.playlist_name] = playlist.data
        self.cog.bot.loop.create_task(
            interaction.edit_original_message(content={
                "ja": "削除しました。", "en": "Removed"
            }, embed=None, view=None)
        )


class ShowPlaylistSelect(PlaylistSelect):
    "プレイリストの曲を表示する時のプレイリスト選択に使うSelect"

    async def callback(self, interaction: discord.Interaction):
        view = PlaylistMusics(self.values[0], self.cog, self.cog.get_playlist(
            interaction.user.id, self.values[0]
        ).to_musics(self.cog, interaction.user))
        await interaction.response.edit_message(content=None, embed=view.data[0], view=view)


class PlayPlaylistSelect(PlaylistSelect):
    "プレイリストの曲を全て再生またはキューに追加する際に使うSelect"

    async def callback(self, interaction: discord.Interaction):
        await self.cog._play(
            Context(self.cog.bot, interaction, self.cog.play, "rt!play"),
            self.cog.get_playlist(interaction.user.id, self.values[0]).to_musics(
                self.cog, interaction.user
            )
        )