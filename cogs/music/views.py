# RT.cogs.music - Views ... 音楽プレイヤーで使うViewのモジュールです。

from typing import Optional, Union, Type, List

from discord.ext import commands
import discord

from .music_player import MusicPlayer
from .cogs.music import MusicData
from .util import check_dj


def split_list(list_: list, n: int = 10) -> List[list]:
    # リストを分ける関数です。
    for idx in range(0, len(list_), n):
        yield list_[idx:idx + n]


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
        self, player: MusicPlayer,
        target: discord.Member, mode: str, *args, **kwargs
    ):
        self.palyer: MusicPlayer = player
        self.queues: List[List[MusicData]] = split_list(player.queues)
        self.now_queues: List[MusicData] = []
        self.length: int = len(self.queues)
        self.music_count: int = len(player.queues)
        self.target: discord.Member = target
        self.mode: str = mode
        self.page: int = 0

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
                embed = self.make_embed()
            except IndexError:
                self.page = before
            else:
                await self.on_update()
                await interaction.response.edit_message(
                    embed=embed
                )

    @discord.ui.button(emoji="◀️")
    async def left(self, button, interaction):
        await self.on_button(button, interaction)

    @discord.ui.button(emoji="▶️")
    async def right(self, button,interaction):
        await self.on_button(button, interaction)

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
        max_: int = 10, **kwargs
    ):
        self.cog = cog
        self.queues: List[MusicData] = queues

        kwargs["max_values"] = max_
        kwargs["options"] = make_options(queues)
        super().__init__(**kwargs)


class QueueSelect(MusicSelect):
    async def callback(self, interaction: discord.Interaction):
        if check_dj(interaction.user):
            for value in self.values:
                self.cog.now[interaction.message.guild.id].remove_queue(
                    self.queues[int(value)]
                )
            await interaction.response.send_message(                    
                {"ja": f"{interaction.user.mention}, キューを削除しました。",
                 "en": f"{interaction.user.mention}, Removed queue."}
            )
        else:
            await interaction.respone.send_message(
                {"ja": f"{interaction.user.mention}, 他の人がいるのでこの操作をするには`DJ`役職が必要です。",
                 "en": f"{interaction.user.mention}, The `DJ` role is required to perform this operation as others are present."}
            )


class QueuesView(MusicListView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cog = self.player.cog
        self.add_item(QueueSelect(self.cog, self.now_queues))

    async def on_update(self):
        for child in self.children:
            if hasattr(child, "values"):
                child.options = make_options(self.now_queues)
