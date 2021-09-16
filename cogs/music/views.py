# RT.cogs.music - Views ... 音楽プレイヤーで使うViewのモジュールです。

from typing import Optional, Union, Type, List

from discord.ext import commands
import discord

from functools import wraps

from .music_player import MusicPlayer
from .cogs.music import MusicData
from .util import check_dj


def split_list(list_: list, n: int = 10) -> List[list]:
    # リストを分ける関数です。
    data = []
    for idx in range(0, len(list_), n):
        data.append(list_[idx:idx + n])
    return data


class MusicListView(discord.ui.View):

    TITLES = {
        "queues": {
            "ja": "キュー",
            "en": "Queue"
        },
        "playlist": {
            "ja": "プレイリスト",
            "en": "Playlist"
        }
    }

    def __init__(
        self, player: MusicPlayer, target: discord.Member,
        mode: str, *args, extras: dict = {}, **kwargs
    ):
        self.player: MusicPlayer = player
        self.queues: List[List[MusicData]] = split_list(player.queues)
        self.now_queues: List[MusicData] = self.queues[0]
        self.length: int = len(self.queues)
        self.music_count: int = len(player.queues)
        self.target: discord.Member = target
        self.mode: str = mode
        self.page: int = 0
        self.extras: dict = extras

        super().__init__(*args, **kwargs)

    def make_embed(
        self, color: Optional[Union[discord.Color, str]] = None
    ) -> discord.Embed:
        # 現在のページからキューリストのEmbedを作ります。
        color = self.bot.colors[color] if isinstance(color, str) else color
        self.now_queues = self.queues[self.page]
        embed = discord.Embed(
            title=self.TITLES[self.mode],
            description="\n".join(
                f"{queue.author.mention}：{queue.title_url}"
                for queue in self.now_queues
            ),
            color=discord.Embed.Empty if color is None else color
        )
        embed.set_footer(
            text=f"Pages {self.page}/{self.length} | {self.music_count} songs"
        )
        return embed

    async def on_button(
        self, mode: str, button: discord.ui.Button,
        interaction: discord.Interaction
    ):
        if interaction.user.id == self.target.id:
            before = self.page
            self.page = self.page + 1 if mode == "right" else -1
            try:
                embed = self.make_embed(
                    self.player.cog.bot.colors["queue"]
                )
            except IndexError:
                self.page = before
            else:
                await self.on_update()
                await interaction.response.edit_message(
                    embed=embed
                )

    @discord.ui.button(emoji="◀️")
    async def left(self, button, interaction):
        await self.on_button("left", button, interaction)

    @discord.ui.button(emoji="▶️")
    async def right(self, button,interaction):
        await self.on_button("right", button, interaction)

    async def on_update(self):
        ...


def make_options(queues: List[MusicData]) -> List[discord.SelectOption]:
    i = -1
    return [
        discord.SelectOption(
            label=queue.title, value=str(i), description=queue.url
        )
        for queue in queues if (i := i + 1) or True
    ]


class MusicSelect(discord.ui.Select):
    def __init__(
        self, cog: Type[commands.Cog], queues: List[MusicData],
        max_: int = 10, extras: dict = {}, **kwargs
    ):
        self.cog: Type[commands.Cog] = cog
        self.queues: List[MusicData] = queues
        self.extras: dict = extras

        length = len(queues)
        kwargs["options"] = make_options(queues)
        kwargs["max_values"] = max_ if length > max_ else length

        super().__init__(**kwargs)


class OptionsView(MusicListView):
    async def on_update(self):
        for child in self.children:
            if hasattr(child, "values"):
                child.options = make_options(self.now_queues)


class QueueSelect(MusicSelect):
    async def callback(self, interaction: discord.Interaction):
        if check_dj(interaction.user):
            for value in self.values:
                self.cog.now[interaction.message.guild.id].remove_queue(
                    self.queues[int(value)]
                )
            await interaction.response.edit_message(                    
                content={
                    "ja": f"{interaction.user.mention}, キューを削除しました。",
                    "en": f"{interaction.user.mention}, Removed queue."
                },
                embed=None, view=None
            )
        else:
            await interaction.respone.send_message(
                content={
                    "ja": f"{interaction.user.mention}, 他の人がいるのでこの操作をするには`DJ`役職が必要です。",
                    "en": f"{interaction.user.mention}, The `DJ` role is required to perform this operation as others are present."
                }
            )


class QueuesView(OptionsView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_item(
            QueueSelect(
                self.player.cog, self.now_queues[1:],
                placeholder="キューの削除"
            )
        )


class PlaylistMusicSelect(MusicSelect):
    async def callback(self, interaction):
        if interaction.user.id == self.view.target.id:
            await self.selected(
                interaction, (
                    self.queues[int(value)]
                    for value in self.values
                )
            )

    async def selected(self, interaction, queues):
        ...


class PlaylistMusicSelectDelete(PlaylistMusicSelect):
    async def selected(self, interaction, queues):
        for queue in queues:
            await self.cog.delete_playlist_item(
                interaction.user.id, self.view.extras["name"],
                queue.to_dict()
            )
        await interaction.edit_message(
            content="プレイリストから指定された曲を削除しました。",
            embed=None, view=None
        )


async def _wrap(coro, **kwargs):
    @wraps(coro)
    async def new_coro(self, *args, **real_kwargs):
        kwargs.update(real_kwargs)
        return await coro(self, *args, **kwargs)
    return new_coro


class PlaylistMusicSelectPlay(PlaylistMusicSelect):
    async def selected(self, interaction, queues):
        ctx = await self.cog.bot.get_context(interaction.message)
        ctx.reply = _wrap(
            interaction.response.edit_message,
            embed=None, view=None
        )
        await self.cog.play(ctx, "", queues)


class PlaylistMusicListView(OptionsView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_item(
            PlaylistMusicSelectDelete(
                self.player.cog, self.now_queues,
                placeholder="曲の削除"
            )
        )
        if self.target.guild.id in self.player.cog.now:
            self.add_item(
                PlaylistMusicSelectPlay(
                    self.player.cog, self.now_queues,
                    placeholder="曲を再生"
                )
            )


class FalsePlayer:
    def __init__(self, cog, queues):
        self.cog, self.queues = cog, queues


class PlaylistSelect(discord.ui.Select):
    def __init__(self, cog: Type[commands.Cog], *args, **kwargs):
        self.cog: Type[commands.Cog] = cog
        super().__init__(*args, **kwargs)

    async def callback(self, interaction):
        data = await self.cog.read_playlists(
            interaction.user.id, self.values[0]
        )
        view = PlaylistMusicListView(
            FalsePlayer(
                self.cog, [
                    data.update({"get_source": None})
                    or MusicData(data, interaction.user)
                    for data in data[self.values[0]]
                    if data
                ]
            ), interaction.user, "playlist",
            extras={"name": self.values[0]}
        )
        await interaction.response.edit_message(
            embed=view.make_embed(self.cog.bot.colors["queue"]),
            view=view
        )


class PlaylistView(discord.ui.View):
    def __init__(
        self, playlists: List[str],
        cog: Type[commands.Cog], *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.add_item(
            PlaylistSelect(
                cog, options=[
                    discord.SelectOption(
                        label=playlist, value=playlist
                    ) for playlist in playlists
                ], placeholder="プレイリスト一覧"
            )
        )


class AddToPlaylistSelect(discord.ui.Select):
    async def callback(self, interaction):
        if interaction.user.id == self.view.target.id:
            for music in self.view.musics:
                await self.view.cog.write_playlist(
                    interaction.user.id, self.values[0],
                    music.to_dict()
                )
            await interaction.response.edit_message(
                content="プレイリストに曲を追加しました。",
                view=None
            )


class AddToPlaylist(discord.ui.View):
    def __init__(
        self, cog: Type[commands.Cog], target: discord.Member,
        queues: List[MusicData], playlists: List[str], *args, **kwargs
    ):
        self.cog: Type[commands.Cog] = cog
        self.musics: List[MusicData] = queues
        self.target: discord.Member = target

        super().__init__(*args, **kwargs)

        self.add_item(
            AddToPlaylistSelect(
                options=[
                    discord.SelectOption(
                        label=playlist, value=playlist
                    ) for playlist in playlists
                ], placeholder="プレイリスト選択"
            )
        )
