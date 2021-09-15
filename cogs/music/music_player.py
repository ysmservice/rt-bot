# RT.cogs.music - Music Player ... 音楽プレイヤーを使用しているサーバーに割り当てる音楽プレイヤークラスのモジュールです。

from typing import Optional, Union, Type, Callable, List

from discord.ext import commands
import discord

from .cogs.music import MusicData


class MusicPlayer:

    MAX = 800

    def __init__(self, cog: Type[commands.Cog], guild: discord.Guild):
        self.cog: Type[commands.Cog] = cog
        self.guild: discord.Guild = guild
        self.vc: discord.VoiceClient = guild.voice_client

        self.queues: List[MusicData] = []
        self.length: int = 0
        self.loop: bool = False

    def add_queue(self, music: MusicData) -> None:
        if self.length == self.MAX:
            raise OverflowError("追加しすぎです。")
        else:
            self.queues.append(music)
            self.length += 1

    def remove_queue(self, index: Union[int, MusicData]) -> None:
        if isinstance(index, int):
            del self.queues[index]
        else:
            self.queues.remove(index)
        self.length -= 1

    def read_queue(self, index: int) -> MusicData:
        return self.queues[index]

    async def _after(self, e):
        # 再生終了後に呼び出される関数で後処理をする。
        self.queues[0].close()
        if e:
            print("Error on Music:", e)
        if not self.loop:
            self.remove_queue(0)
        await self.play()

    async def play(self) -> bool:
        # 音楽を再生する関数です。
        if self.queues:
            queue = self.queues[0]
            queue.started()
            self.vc.play(
                await queue.get_source(),
                after=lambda e: self.cog.bot.loop.create_task(
                    self._after(e)
                )
            )
            return True
        return False

    def skip(self) -> None:
        self.voice_client.stop()

    def pause(self) -> bool:
        if self.voice_client.is_paused():
            self.voice_client.resume()
            return True
        else:
            self.voice_client.pause()
            return False

    def loop(self) -> bool:
        self.loop = not self.loop
        return self.loop

    EMBED_TITLE = {
        "ja": "現在再生中の音楽",
        "en": "Now playing"
    }

    def embed(self, index: int = 0) -> Optional[discord.Embed]:
        if self.queues:
            queue = self.queues[index]
            embed = discord.Embed(
                title=self.EMBED_TITLE,
                url=queue.url,
                color=self.cog.bot.colors["normal"]
            )
            embed.set_author(
                name=queue.author.display_name,
                icon_url=getattr(queue.author.avatar, "url", "")
            )
            embed.set_footer(text=queue.make_seek_bar())
            embed.set_image(url=queue.thumbnail)
            embed.add_field(
                name={"ja": "タイトル", "en": "Title"},
                value=queue.title
            )
            embed.add_field(
                name={"ja": "時間", "en": "Elapsed time"},
                value=queue.elapsed
            )
            return embed
        else:
            return None
