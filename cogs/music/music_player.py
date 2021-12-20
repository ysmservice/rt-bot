# RT.cogs.music - Music Player ... 音楽プレイヤーを使用しているサーバーに割り当てる音楽プレイヤークラスのモジュールです。

from typing import Optional, Union, Type, Callable, List

from discord.ext import commands
import discord

from random import shuffle
from time import time

from .cogs.music import MusicData
from .cogs import make_get_source


class MusicPlayer:

    MAX = 800

    def __init__(
        self, cog: Type[commands.Cog], guild: discord.Guild,
        channel: discord.TextChannel
    ):
        self.cog: Type[commands.Cog] = cog
        self.guild: discord.Guild = guild
        self.channel: discord.TextChannel = channel
        self.voice_client: discord.VoiceClient = guild.voice_client

        self.queues: List[MusicData] = []
        self.length: int = 0
        self._loop: bool = False
        self.before: float = 0
        self.first: bool = False
        self.force_end: bool = False

    def add_queue(self, music: MusicData) -> None:
        music._make_get_source = make_get_source
        if self.length == self.MAX:
            raise OverflowError("追加しすぎです。")
        else:
            self.queues.append(music)
            self.length += 1

    def remove_queue(self, index: Union[int, MusicData]) -> None:
        if isinstance(index, int):
            try:
                del self.queues[index]
            except IndexError:
                pass
        else:
            self.queues.remove(index)
        self.length -= 1

    def read_queue(self, index: int) -> MusicData:
        return self.queues[index]

    async def _after(self, e, error: bool = False, c: int = 0):
        # 再生終了後に呼び出される関数で後処理をする。
        if self.queues:
            self.queues[0].close()
        if e:
            print("Error on Music:", e)
        if not self._loop or error:
            self.remove_queue(0)
            if c == 4:
                return self.remove_queue(0)

        if not self.force_end and self.queues:
            try:
                await self.play()
            except Exception as e:
                await self.channel.send(
                    f"何らかのエラーにより`{self.queues[0].title}`が再生ができませんでした。".replace(
                        "@", "＠"
                    )
                )
                self.cog.bot.loop.create_task(self._after(None, True, c + 1))

    async def play(self) -> bool:
        # 音楽を再生する関数です。
        if self.queues and not self.voice_client.is_playing():
            queue = self.queues[0]
            queue.started()
            self.before = 0
            self.first = False
            try:
                self.voice_client.play(
                    await queue.get_source(),
                    after=lambda e: self.cog.bot.loop.create_task(
                        self._after(e)
                    )
                )
            except discord.ClientException:
                return False
            return True
        return False

    def clear(self) -> None:
        self.queues = self.queues[:1]
        self.length = 1

    def skip(self) -> None:
        if self._loop:
            self.remove_queue(0)
        self.voice_client.stop()
        self.before = time()

    def pause(self) -> bool:
        if self.voice_client.is_paused():
            self.voice_client.resume()
            self.queues[0].started()
            self.before = 0
            return True
        else:
            self.voice_client.pause()
            self.queues[0].stopped()
            self.before = time()
            return False

    def loop(self) -> bool:
        self._loop = not self._loop
        return self._loop

    def shuffle(self) -> None:
        if self.length > 1:
            queues = self.queues[1:]
            shuffle(queues)
            self.queues = self.queues[:1] + queues

    def check_timeout(self, t: int = 300) -> bool:
        if self.before == 0:
            return False
        else:
            return time() - self.before > t

    EMBED_TITLE = {
        "ja": "現在再生中の音楽",
        "en": "Now playing"
    }

    def embed(self, index: int = 0) -> Optional[discord.Embed]:
        if self.queues:
            queue = self.queues[index]
            embed = discord.Embed(
                title=self.EMBED_TITLE,
                description=queue.make_seek_bar(),
                color=self.cog.bot.colors["player"]
            )
            embed.set_author(
                name=queue.author.display_name,
                icon_url=getattr(queue.author.avatar, "url", "")
            )
            embed.set_image(url=queue.thumbnail)
            embed.add_field(
                name={"ja": "タイトル", "en": "Title"},
                value=f"[{queue.title}]({queue.url})"
            )
            embed.add_field(
                name={"ja": "時間", "en": "Elapsed time"},
                value=queue.elapsed
            )
            return embed
        else:
            return None
