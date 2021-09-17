# RT.cogs.music.cogs - ニコニコ動画 ... ニコニコ動画のAudioSourceを取得するためのモジュールです。

from typing import TYPE_CHECKING

from niconico_dl import NicoNicoVideoAsync
import discord
import asyncio

from .classes import MusicRawData, UploaderData
from .youtube import BEFORE_OPTIONS, OPTIONS
from .music import MusicData


async def get_music(
    url: str, author: discord.Member,
    loop: asyncio.AbstractEventLoop, **kwargs
) -> MusicData:
    nico = NicoNicoVideoAsync(url, loop=loop, **kwargs)
    data = await nico.get_info()

    async def _get_source():
        await nico.connect()
        return discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(
                await nico.get_download_link(),
                before_options=BEFORE_OPTIONS,
                options=OPTIONS
            )
        ), nico.close

    return MusicData(
        MusicRawData(
            url=url, title=data["video"]["title"],
            thumbnail=data["video"]["thumbnail"]["url"],
            duration=data["video"]["duration"], uploader=UploaderData(
                name=data["owner"]["nickname"],
                url=f"https://www.nicovideo.jp/user/{data['owner']['id']}"
            ), get_source=_get_source
        ), author
    )


if __name__ == "__main__":
    print(asyncio.run(get_music(input(">"), 1)).raw_data)
