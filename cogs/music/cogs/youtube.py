# RT.music.cogs - YouTube ... YouTubeのAudioSourceを取得するためのものです。

from typing import List

from youtube_dl import YoutubeDL
import discord
import asyncio

from .classes import MusicRawData, UploaderData, GetSource
from .music import MusicData


def get_thumbnail_url(video_id: str) -> str:
    return f"http://i3.ytimg.com/vi/{video_id}/hqdefault.jpg"


BEFORE_OPTIONS = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
OPTIONS = "-vn"
DOWNLOAD_OPTIONS = {
    "format": "bestaudio/best",
    "default_search": "auto",
    "logtostderr": False,
    "cachedir": False,
    "ignoreerrors": True,
    "source_address": "0.0.0.0"
}
FLAT_OPTIONS = {
    "extract_flat": True,
    "source_address": "0.0.0.0"
}


async def _get(
    loop: asyncio.AbstractEventLoop, url: str,
    options: dict, download: bool = False
) -> dict:
    # 渡されたものからデータを取得する。
    return await loop.run_in_executor(
        None, lambda : YoutubeDL(options).extract_info(
            url, download=download
        )
    )


def _make_get_source(
    loop: asyncio.AbstractEventLoop, url: str,
    options: dict = DOWNLOAD_OPTIONS
) -> GetSource:
    # AudioSourceを取得する関数を取得する関数です。
    async def _get_source():
        data = await _get(loop, url, options)
        return discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(
                data["url"], before_options=BEFORE_OPTIONS,
                options=OPTIONS
            )
        ), lambda : None
    return _get_source


def _make_music_raw_data(
    loop: asyncio.AbstractEventLoop, data: dict
) -> MusicRawData:
    return MusicRawData(
        url=(url := f"https://www.youtube.com/watch?v={data.get('display_id', data.get('id'))}"),
        title=data["title"], thumbnail=data["thumbnail"],
        duration=data["duration"], uploader=UploaderData(
            name=data["uploader"], url=data.get("uploader_url")
        ), get_source=_make_get_source(loop, url)
    )


async def get_music(
    url: str, author: discord.Member,
    loop: asyncio.AbstractEventLoop, *,
    download: bool = False
) -> MusicData:
    # 曲単体の情報を取得します。
    return MusicData(
        _make_music_raw_data(
            loop,
            await _get(loop, url, FLAT_OPTIONS, download)
        ), author
    )


async def get_playlist(
    url: str, author: discord.Member,
    loop: asyncio.AbstractEventLoop, *,
    download: bool = False
) -> List[MusicData]:
    # プレイリストにある曲の情報を取得します。またytsearchで検索もできます。
    loop = loop or asyncio.get_event_loop()
    data = await _get(loop, url, FLAT_OPTIONS)
    return [
        MusicData(
            _make_music_raw_data(
                loop, {
                    "title": entrie["title"], "id": entrie["id"],
                    "thumbnail": get_thumbnail_url(entrie["id"]),
                    "duration": entrie["duration"], "uploader": entrie["uploader"]
                }
            ), author
        ) for entrie in data["entries"]
    ]


if __name__ == "__main__":
    from ujson import dump
    loop = asyncio.get_event_loop()
    with open("./test.json", "w") as f:
        dump(loop.run_until_complete(get_music(input(">"), 1, loop)).raw_data, f, indent=4)
