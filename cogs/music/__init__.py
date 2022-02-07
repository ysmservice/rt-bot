# RT - Music

from typing import TypeVar, Callable, Union, Optional, Any

from functools import wraps

import discord.ext.commands as commands
import discord

from aiohttp import ClientSession
from ujson import dumps

from rtlib import RT, Table

from .views import Confirmation
from .music import MusicDict, Music
from .player import Player


class DJData(Table):
    __allocation__ = "GuildID"
    dj: int


class UserData(Table):
    __allocation__ = "UserID"
    playlists: dict[str, list[MusicDict]]


DecoT = TypeVar("DecoT")
def check(
    headding: dict[str, str], check_state: bool = True, check_dj: bool = True
) -> Callable[[DecoT], DecoT]:
    """音楽再生コマンドにつけるデコレータです。
    権限の確認等を行います。また、見出しをつけます。"""
    async def decorator(func):
        @wraps(func)
        async def new(self: MusicCog, ctx: commands.Context, *args, **kwargs):
            if not check_state:
                return await func()

            if ctx.message.author.voice is None:
                await ctx.reply(
                    {"ja": "ボイスチャンネルに接続してください。",
                     "en": "You must be connected to a voice channel."}
                )
            elif ctx.guild.voice_client is None:
                return await ctx.reply(
                    {
                        "ja": "自分ボイスチャンネルに参加していないです。音楽再生をしてください。\n"
                            "*P.S.* もしボイスチャンネルにいるのにこうなる場合は`rt!disconnect force`を実行してください。",
                        "en": "I have not joined my own voice channel. Please play the music.\n"
                            "*P.S.* If this happens while you are on the voice channel, run `rt!disconnect force`."
                    }
                )
            elif len(
                members := [
                    member for member in ctx.author.voice.channel.members
                    if not member.bot
                ]
            ) > 1 \
                    and check_dj and "dj" in self.data[ctx.author.id] \
                    and ctx.author.get_role(self.data[ctx.author.id].dj) is None:
                # DJがないといけないのに持っていない場合はコマンドを実行して良いか募集する。
                view = Confirmation(func.callback(self, ctx, *args, **kwargs), members, ctx)
                view.message = await ctx.reply(
                    {
                        "ja": "他の人がいも音楽を聞いている場合はDJ役職がなければこのコマンドを実行することができません。\n"
                            "または、以下のボタンをボイスチャンネルにいる人全員が押せば実行することができます。",
                        "en": "If other people are also listening to the music, you will not be able to execute this command without a DJ role.\n"
                            "Or, it can be done by having everyone in the voice channel press the following button."
                    }, view=view
                )
            else:
                # チェックが済んだならメインを実行する。
                return await func.callback(self, ctx, *args, **kwargs)
        if "headding" not in func.extras:
            func.extras["headding"] = headding
        func._callback = new
        return new
    return decorator


class MusicCog(commands.Cog):
    def __init__(self, bot: RT):
        self.bot = bot
        self.client_session = ClientSession(json_serialize=dumps)
        self.now: dict[int, Player] = {}
        self.dj, self.data = DJData(self.bot), UserData(self.bot)

    def print(self, *args, **kwargs):
        "デバッグ用とかっこつけるためのprintです。"
        return self.bot.print("[MusicPlayer]", *args, **kwargs)

    def max(self, member: Union[discord.Member, discord.Guild] = None) -> int:
        "最大曲数を取得します。"
        return 800

    @commands.command()
    @check({"ja": "音楽再生をします。", "en": "Play music"}, False)
    async def play(self, ctx: commands.Context, *, url: str):
        if ctx.guild.id not in self.now:
            self.now[ctx.guild.id] = Player(self, ctx.guild)
        self.now[ctx.guild.id].add_from_url(url)
        ...

    def cog_unload(self):
        # コグがアンロードされた際にもし使用されてる音楽プレイヤーがあれば終了する。
        for player in self.now.values():
            self.bot.loop.create_task(
                player.disconnect(
                    {"ja": "すみませんが再起動または音楽プレイヤーの更新のため音楽再生を終了します。",
                     "en": "Sorry, music playback will be terminated due to reboot or music player update."}
                ), name=f"{player}.disconnect"
            )


def setup(bot):
    bot.add_cog(Music(bot))
