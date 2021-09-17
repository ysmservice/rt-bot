# RT.music.cogs - Music ... 音楽のデータをまとめるためのクラスのモジュールです。

from typing import TYPE_CHECKING, Optional, Type, Literal

from time import time
from copy import copy
import discord

from .classes import (
    MusicRawData, UploaderData, GetSource, MusicRawDataForJson
)
if TYPE_CHECKING:
    from .__init__ import make_get_source
else:
    make_get_source = None


class MusicData:
    def __init__(
        self, music: MusicRawData, author: discord.Member,
        make_get_source: Literal[make_get_source, None] = None
    ):
        self.url: str = music["url"]
        self.title: str = music["title"]
        self.uploader: UploaderData = music["uploader"]
        self.thumbnail: str = music["thumbnail"]
        self.duration: Optional[int] = music.get("duration")
        self.duration_str: Optional[str] = (
            self.time_str(self.duration) if self.duration else None
        )
        self._get_source: GetSource = music["get_source"]
        self.author: discord.Member = author
        self.raw_data: MusicRawData = music

        self.start: int = 0
        self._stop = 0
        self._make_get_source: Literal[make_get_source, None] = make_get_source

    def to_dict(self) -> MusicRawDataForJson:
        # JSON形式で保存可能な辞書で音楽データを取得します。
        data = copy(self.raw_data)
        del data["get_source"]
        return data

    @property
    def uploader_text(self) -> str:
        # 音楽の投稿者の名前とURLを取得します。
        name = self.uploader["name"]
        if self.uploader["url"]:
            name = f"[{self.uploader['name']}]({self.uploader['url']})"
        return name

    async def get_source(self) -> Type[discord.FFmpegPCMAudio]:
        # AudioSourceを取得する関数です。

        if self._get_source is None:
            # プレイリストから追加された音楽の場合はget_sourceがないので取得する。
            self._get_source = await self._make_get_source(
                self.url, self.author
            )

        # AudioSourceを作る。
        source, self._close = await self._get_source()
        return source

    def close(self):
        # 音楽再生後に実行すべき関数です。
        self._close()

    @property
    def title_url(self) -> str:
        # タイトルをマークダウンのURLでカバーした文字列にして取得する関数です。
        return f"[{self.title}]({self.url})"

    def started(self, extras: int = 0) -> None:
        # 音楽再生時に呼び出すべき関数です。
        self.start = time() + self._stop

    def stopped(self) -> None:
        self._stop = time()

    def time_str(self, t: int) -> str:
        # 秒数を`01:39`のような`分：秒数`の形にする。
        return ":".join(
            map(lambda o: (
                str(int(o[1])).zfill(2)
                if o[0] or o[1] <= 60
                else self.time_str(o[1])
            ), ((0, t // 60), (1, t % 60)))
        )

    @property
    def now(self) -> int:
        # 何秒再生してから経過したかを取得する関数です。
        return time() - self.start

    @property
    def now_str(self) -> str:
        # 何秒再生してから経過したかを文字列にして取得する関数です。
        return self.time_str(self.now)

    @property
    def elapsed(self) -> str:
        # 何秒経過したかの文字列を取得する関数です。
        return f"{self.now_str}/{self.duration_str}"

    def make_seek_bar(self, length: int = 15) -> str:
        # どれだけ音楽が再生されたかの絵文字によるシークバーを作る関数です。
        return "".join((
            (base := "◾" * length
            )[:(now := int(self.now / self.duration * length))],
            "⬜", base[now:])
        )

    def __str__(self):
        return f"<MusicData Title:{self.title} Elapsed:{self.elapsed} Url:{self.url}>"
