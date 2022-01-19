# RT.cogs.music - Views ... 音楽プレイヤーで使うViewのモジュールです。

from typing import Optional, Union, Type, List, Dict

from discord.ext import commands
import discord

from functools import wraps

from .cogs.classes import MusicRawDataForJson
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
    """音楽のリストのメニューのViewです。"""

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
                f"{(queue.author.mention + '：') if self.mode == 'queues' else ''}{queue.title_url}"
                for queue in self.now_queues
            ),
            color=discord.Embed.Empty if color is None else color
        )
        embed.set_footer(
            text=f"Pages {self.page + 1}/{self.length} | {self.music_count} songs"
        )
        return embed

    async def on_button(
        self, mode: str, button: discord.ui.Button,
        interaction: discord.Interaction
    ):
        if interaction.user.id == self.target.id:
            before = self.page
            if mode.endswith("skip"):
                self.page = 0 if mode.startswith("left") else self.length - 1
            else:
                self.page = self.page + (1 if mode == "right" else -1)

            try:
                if self.page == -1:
                    raise IndexError("範囲外")
                else:
                    embed = self.make_embed(
                        self.player.cog.bot.colors["queue"]
                    )
            except IndexError as e:
                self.page = before
            else:
                # Viewに登録されているセレクトにある音楽を次のページのものに交換する。
                for child in self.children:
                    if hasattr(child, "options"):
                        child.options = make_options(self.now_queues)
                        child.queues = self.now_queues
                        length = len(self.now_queues)
                        child.max_values = (
                            child.max_values if length >= child.max_values
                            else length
                        )

                await self.on_update()

                await interaction.response.edit_message(
                    embed=embed, view=self
                )

    @discord.ui.button(emoji="⏮️")
    async def left_skip(self, button, interaction):
        await self.on_button("left_skip", button, interaction)

    @discord.ui.button(emoji="◀️")
    async def left(self, button, interaction):
        await self.on_button("left", button, interaction)

    @discord.ui.button(emoji="▶️")
    async def right(self, button,interaction):
        await self.on_button("right", button, interaction)

    @discord.ui.button(emoji="⏭️")
    async def right_skip(self, button,interaction):
        await self.on_button("right_skip", button, interaction)

    async def on_update(self):
        ...


def parse_length(text: str, max_: int = 100) -> str:
    return text[:99] if len(text) > max_ else text


def make_options(queues: List[MusicData]) -> List[discord.SelectOption]:
    # 音楽データからdiscord.SelectOptionのリストを作ります。
    i = -1
    return [
        discord.SelectOption(
            label=parse_length(queue.title), value=str(i),
            description=parse_length(queue.url)
        )
        for queue in queues if (i := i + 1) or True
    ]


class MusicSelect(discord.ui.Select):
    """音楽を選択するSelectのクラスです。"""
    def __init__(
        self, cog: Type[commands.Cog], queues: List[MusicData],
        max_: int = 10, extras: dict = {}, **kwargs
    ):
        self.cog: Type[commands.Cog] = cog
        self.queues: List[MusicData] = queues
        self.extras: dict = extras

        length = len(queues)
        kwargs["options"] = make_options(queues)
        kwargs["max_values"] = max_ if length >= max_ else length

        super().__init__(**kwargs)


class QueueSelectForDelete(MusicSelect):
    """キューが選択された際にそのキュー削除するということをするセレクトのクラスです。"""
    async def callback(self, interaction: discord.Interaction):
        interaction.author = interaction.user
        if check_dj(interaction.user, interaction):
            for value in self.values:
                self.cog.now[interaction.message.guild.id].remove_queue(
                    self.queues[int(value)]
                )
            await interaction.response.edit_message(                    
                content={
                    "ja": "キューを削除しました。",
                    "en": "Removed queue."
                }, embed=None, view=None
            )
        else:
            await interaction.respone.send_message(
                content={
                    "ja": "他の人がいるのでこの操作をするには`DJ`役職が必要です。",
                    "en": "The `DJ` role is required to perform this operation as others are present."
                }
            )


class QueueSelectForAddToPlaylist(MusicSelect):
    """キューにあるものを選択された際にプレイリストに追加するセレクトのクラスです。"""
    async def callback(self, interaction: discord.Interaction):
        playlists = await self.cog.get_playlists(interaction.user.id)
        if playlists:
            await interaction.response.send_message(
                content={
                    "ja": "どのプレイリストに追加するか選択してください。",
                    "en": "Please select the playlist."
                }, ephemeral=True, view=AddToPlaylist(
                    self.cog, self.view.now_queues, playlists
                )
            )
        else:
            await interaction.response.send_message(
                content="プレイリストをあなたは作っていません。",
                ephemeral=True
            )


class QueuesView(MusicListView):
    """キューのリストのメニューを作るViewです。"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_item(
            QueueSelectForDelete(
                self.player.cog, self.now_queues[1:],
                placeholder="キューの削除"
            )
        )
        self.add_item(
            QueueSelectForAddToPlaylist(
                self.player.cog, self.now_queues,
                placeholder="プレイリストに追加"
            )
        )


# ここからプレイリスト関連のクラスです。


class PlaylistMusicSelect(MusicSelect):
    """プレイリストにある音楽を選択された際に音楽データをselectedに渡して実行する、という処理をするセレクトのクラスです。
    継承して使います。"""
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
    """プレイリストで音楽を消すということをするセレクトのクラスです。"""
    async def selected(self, interaction, queues):
        for queue in queues:
            await self.cog.delete_playlist_item(
                interaction.user.id, self.view.extras["name"],
                queue.to_dict()
            )
        await interaction.response.edit_message(
            content="プレイリストから指定された曲を削除しました。",
            embed=None, view=None
        )


def _wrap(coro, **kwargs):
    # 指定されたコルーチン関数を指定されたキーワード引数を自動で渡して実行するものに変える関数です。
    @wraps(coro)
    async def new_coro(*args, **real_kwargs):
        kwargs.update(real_kwargs)
        return await coro(*args, **kwargs)
    return new_coro


class PlaylistMusicSelectPlay(PlaylistMusicSelect):
    """プレイリストから音楽を再生するセレクトのクラスです。"""
    async def selected(self, interaction, queues):
        ctx = await self.cog.bot.get_context(interaction.message)
        ctx.reply = _wrap(
            interaction.response.edit_message,
            embed=None, view=None
        )
        await self.cog.play(ctx, song="", datas=queues)


class PlaylistMusicListView(MusicListView):
    """プレイリストの音楽のリストのメニューのViewです。"""
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
    """音楽プレイヤークラスの../music_player.pyにあるMusicPlayerの偽物です。
    これを使わないと実現できないものがあるためこのクラスがあります。"""
    def __init__(self, cog, queues):
        self.cog, self.queues = cog, queues


class PlaylistSelect(discord.ui.Select):
    """選択されたプレイリストにある曲のメニューを表示するセレクトのクラスです。"""
    def __init__(
        self, cog: Type[commands.Cog], playlists: List[str],
        *args, extras=None, **kwargs
    ):
        self.cog: Type[commands.Cog] = cog
        self.extras = extras
        super().__init__(
            *args, options=[
                discord.SelectOption(
                    label=playlist, value=playlist
                ) for playlist in playlists
            ], **kwargs
        )

    @staticmethod
    def make_music_data_from_playlist(
        datas: Dict[str, MusicRawDataForJson], author: discord.Member
    ) -> List[MusicData]:
        return [
            data.update({"get_source": None})
            or MusicData(data, author)
            for data in datas
            if data
        ]

    async def callback(self, interaction):
        data = await self.cog.read_playlists(
            interaction.user.id, self.values[0]
        )
        try:
            view = PlaylistMusicListView(
                FalsePlayer(
                    self.cog, self.make_music_data_from_playlist(
                        data[self.values[0]], interaction.user
                    )
                ), interaction.user, "playlist",
                extras={"name": self.values[0]}
            )
        except IndexError:
            await interaction.response.edit_message(
                content="プレイリストが空です。", view=None
            )
        else:
            await interaction.response.edit_message(
                content=None, view=view,
                embed=view.make_embed(self.cog.bot.colors["queue"]),
            )


class PlaylistSelectForQueue(PlaylistSelect):
    """選択されたキューをプレイリストに追加するセレクト"""
    async def callback(self, interaction):
        for music in self.view.musics:
            await self.view.cog.write_playlist(
                interaction.user.id, self.values[0],
                music.to_dict()
            )
        await interaction.response.edit_message(
            content="プレイリストに追加しました。", view=None
        )


class PlaylistSelectViewForQueue(discord.ui.View):
    """選択されたキューをプレイリストに追加するセレクトのViewです。"""
    def __init__(
        self, cog: Type[commands.Cog],
        musics: List[MusicData], *args, **kwargs
    ):
        self.cog = cog
        self.musics = musics

        super().__init__(self, *args, **kwargs)

        self.add_item(
            PlaylistSelectForQueue(cog)
        )


class PlaylistView(discord.ui.View):
    """プレイリストの内容を表示するViewです。"""
    def __init__(
        self, playlists: List[str],
        cog: Type[commands.Cog], *args, **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.add_item(
            PlaylistSelect(
                cog, playlists, placeholder="プレイリスト一覧"
            )
        )


class AddToPlaylistSelect(PlaylistSelect):
    """プレイリストに曲を追加するセレクトのクラスです。"""
    async def callback(self, interaction):
        length = len((
            await self.view.cog.read_playlists(
                interaction.user.id, self.values[0]
            ))[self.values[0]]
        )

        error, musics = "", []
        i = length
        for music in self.view.musics:
            if i == 800:
                error = "\nですが、プレイリストに入れれる楽曲の最大数に達したためいくつかは追加されていません。"
                break
            else:
                i += 1
                musics.append(music.to_dict())

        if i > 15:
            loading = self.view.cog.EMOJIS["loading"]
            await interaction.response.edit_message(
                content={
                    "ja": f"{loading} 追加中です...\n※これには数十秒かかることがあります。",
                    "en": f"{loading} Now saving...\n※This may take a few seconds."
                }, view=None
            )
            del loading
            edit = interaction.edit_original_message
        else:
            edit = interaction.response.edit_message

        await self.view.cog.bulk_write_playlist(
            interaction.user.id, self.values[0], musics
        )
        del musics, i

        await edit(
            content=f"プレイリストに曲を追加しました。{error}"
        )


class AddToPlaylist(discord.ui.View):
    """プレイリストに曲を追加するセレクトのViewです。"""
    def __init__(
        self, cog: Type[commands.Cog], queues: List[MusicData],
        playlists: List[str], *args, **kwargs
    ):
        self.cog: Type[commands.Cog] = cog
        self.musics: List[MusicData] = queues

        super().__init__(*args, **kwargs)

        self.add_item(
            AddToPlaylistSelect(
                cog, playlists, placeholder="プレイリスト選択"
            )
        )
