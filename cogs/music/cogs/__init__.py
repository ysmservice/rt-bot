# RT.music - cogs

from typing import Union, Optional, List

from asyncio import get_running_loop
from aiohttp import ClientSession
import discord
import asyncio

from . import youtube, niconico, soundcloud
from .music import MusicData


async def get_music(
    url: str, author: discord.Member,
    loop: Optional[asyncio.AbstractEventLoop] = None,
    search_max_result: int = 10, client: ClientSession = None, **kwargs
) -> Union[MusicData, List[MusicData]]:
    # 渡されたURLの音楽のデータを取り出します。プレイリストか検索の場合はリストとなります。
    loop = loop or asyncio.get_event_loop()

    if "nicovideo.jp" in url or "nico.ms" in url:
        return await niconico.get_music(url, author, loop, **kwargs)
    elif "www.youtube.com" in url or "youtu.be" in url:
        if "list" in url:
            return await youtube.get_playlist(url, author, loop, **kwargs)
        else:
            return await youtube.get_music(url, author, loop, **kwargs)
    elif "soundcloud.com" in url or "soundcloud.app.goo.gl" in url:
        if "goo" in url:
            async with client.get(url) as r:
                url = str(r.url)
        return await soundcloud.get_music(url, author, loop)
    else:
        return await youtube.get_playlist(
            f"ytsearch{search_max_result}:{url}", author, loop, **kwargs
        )


async def make_get_source(url: str, author: discord.Member):
    loop = get_running_loop()
    if "nico" in url:
        return (
            await niconico.get_music(
                url, author, loop
            )
        )._get_source
    else:
        return youtube._make_get_source(loop, url)
