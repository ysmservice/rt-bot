# RT.music.cogs - Music

from time import time
import discord

from .types import MusicRawData, UploaderData, GetSource


class MusicData:
    def __init__(self, music: MusicRawData, author: discord.Member):
        self.url: str = music["url"]
        self.title: str = music["title"]
        self.uploader: UploaderData = music["uploader"]
        self.thumbnail: str = music["thumbnail"]
        self.duration: int = music["duration"]
        self.duration_str: str = self.time_str(self.duration)
        self._get_source: GetSource = music["get_source"]
        self.author: discord.Member = author

        self.start: int = 0

    async def get_source(self) -> discord.FFmpegPCMAudio:
        return await self._get_source(self.url)

    def start(self) -> None:
        self.start = time()

    def time_str(self, t: int) -> str:
        # 秒数を`01:39`のような`分：秒数`の形にする。
        return ":".join(
            map(lambda o: str(int(o)).zfill(2), (t // 60, t % 60))
        )

    @property
    def now(self) -> int:
        # 何秒再生してから経過したかを取得する関数です。
        return time() - self.start

    @property
    def now_str(self) -> str:
        # 何秒再生してから経過したかを文字列にして取得する関数です。
        return self.time_str(self.now)

    def make_seek_bar(self, length: int = 30) -> str:
        # どれだけ音楽が再生されたかの絵文字によるシークバーを作る関数です。
        return "".join(
            (
                base := "◾" * length
            )[:(now := int(self.now // self.duration * length)],
            "⬜", base[now:]
        )
