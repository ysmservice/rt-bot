# RT.cogs.music - Normal

from typing import Dict

from discord.ext import commands
import discord

from rtlib.slash import Option
from rtlib import componesy
from functools import wraps

from .music_player import MusicPlayer
from .data_manager import DataManager
from .views import QueuesView
from .cogs import get_music
from .util import check_dj


def require_voice(coro):
    # 既に接続して再生する準備が整っている際に実行するようにするデコレータです。
    @wraps(coro)
    async def new_coro(self, ctx, *args, **kwargs):
        if ctx.author.voice and ctx.guild.id in self.now:
            return await coro(self, ctx, *args, **kwargs)
        else:
            await ctx.reply(
                {"ja": "`rt!play URL`を実行してください。",
                 "en": "You must run `rt!play URL`."}
            )
    return new_coro


def require_dj(coro):
    # 他の人がいる場合DJ役職が必要なコマンドに付けるデコレータです。
    @wraps(coro)
    async def new_coro(self, ctx, *args, **kwargs):
        if check_dj(ctx.author):
            return await coro(self, ctx, *args, **kwargs)
        else:
            return await ctx.reply(
                {"ja": "他の人がいるのでこの操作を実行するには`DJ`役職が必要です。",
                 "en": "The `DJ` role is required to perform this operation as others are present."}
            )
    return new_coro


class MusicNormal(commands.Cog, DataManager):

    EMOJIS = {
        "loading": "<a:now_loading:887681011905871872>"
    }
    NOW_LOADING = {
        "ja": f"{EMOJIS['loading']} 読み込み中...",
        "en": f"{EMOJIS['loading']} Now loading..."
    }

    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.init_database())
        self.now: Dict[int, MusicPlayer] = {}

    async def init_database(self):
        super(commands.Cog, self).__init__(self.bot.mysql)
        await self.init_table()

    async def search_result_select(
        self, select: discord.ui.Select, interaction: discord.Interaction
    ):
        # 検索結果を選択された際に呼び出される関数です。
        ctx = await self.bot.get_context(interaction.message)
        ctx.reply = interaction.response.edit_message
        ctx.author = interaction.user
        ctx.interaction = interaction
        await self.play(ctx, song=select.values[0])

    @commands.command(
        slash_command=True,
        description="ボイスチャンネルでYouTube,ニコニコ動画,SoundCloudのどれかを再生します。"
    )
    async def play(
        self, ctx, *,
        song: Option(str, "song", "再生したい曲のURLまたは検索ワードです。")
    ):
        if ctx.guild.id not in self.now:
            # もし接続していないなら接続をする。
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
                self.now[ctx.guild.id] = MusicPlayer(self, ctx.guild)
            else:
                return await ctx.reply(
                    {"ja": "先にボイスチャンネルに接続してください。",
                     "en": "You must connect to voice channel."}
                )

        if hasattr(ctx, "interaction"):
            await ctx.reply(content=self.NOW_LOADING)
            ctx.reply = ctx.interaction.edit_original_message
        else:
            await ctx.trigger_typing()

        # 音楽を取得する。
        datas = await get_music(song, ctx.author, self.bot.loop)
        if isinstance(datas, list):
            i = 0

            if not song.startswith(("https://", "http://")):
                # もし検索の場合はユーザーに何の曲を再生するか聞く。
                view = componesy.View("SongSelect")
                view.add_item(
                    discord.ui.Select, self.search_result_select, placeholder="曲の選択",
                    options=[
                        discord.SelectOption(
                            label=data.title, value=data.url, description=data.url
                        )
                        for data in datas
                    ]
                )
                return await ctx.reply(
                    content="以下の音楽が見つかりました。何を再生するか選んでください。",
                    view=view()
                )
        else:
            i = 1
            datas = [datas]

        # キューに音楽を追加する。
        ext = ("", "")
        for data in datas:
            i += 1
            try:
                self.now[ctx.guild.id].add_queue(data)
            except OverflowError:
                # 800個キューに追加されたらもう追加できないと表示する。。
                ext = (
                    "\nですが、RTは800までしかキューを覚えることができないので800個までしか登録はされていません。",
                    "\nBut RT can only remember up to 800 cues, so only up to 800 cues were added."
                )
                break

        # 再生をする。
        if await self.now[ctx.guild.id].play():
            await ctx.reply(embed=self.now[ctx.guild.id].embed())
        else:
            length = f" Now:{i}"
            await ctx.reply(
                content={
                    "ja": "➕ キューに追加しました。" + length + ext[0],
                    "en": "➕ Added to queues." + length + ext[1]
                }
            )

    @commands.command(
        slash_command=True, description="音楽再生を終了します。",
        aliases=["dis", "leave", "切断", "bye", "せつだん"]
    )
    @require_voice
    @require_dj
    async def disconnect(self, ctx):
        await ctx.guild.voice_client.disconnect()
        del self.now[ctx.guild.id]
        await ctx.reply(
            {"ja": "⏹ 切断しました。",
             "en": "⏹ Disconnected!"}
        )

    @commands.command(
        slash_command=True, description="現在再生している曲の情報を表示します。",
        aliases=["np", "nowplaying", "曲"]
    )
    @require_voice
    async def now(self, ctx):
        if (embed := self.now[ctx.guild.id].embed()):
            await ctx.reply(embed=embed)
        else:
            await ctx.reply(
                {"ja": "✖️ 現在何も再生していません。",
                 "en": "✖️ I'm not playing now."}
            )

    @commands.command(slash_command=True, description="曲をスキップします。")
    @require_voice
    @require_dj
    async def skip(self, ctx):
        self.now[ctx.guild.id].skip()
        await ctx.reply("⏭ Skip!")

    @commands.command(slash_command=True, description="曲をループさせます。")
    async def loop(self, ctx):
        onoff = self.now[ctx.guild.id].loop()
        await ctx.reply(
            f"🔁 {'Loop enabled!' if onoff else 'Loop disabled!'}"
        )

    @commands.command(slash_command=True, description="曲を一時停止または再生を再開します。")
    async def pause(self, ctx):
        play = self.now[ctx.guild.id].pause()
        await ctx.reply("▶️ Resumed!" if play else '⏸ Paused!')

    @commands.command(slash_command=True, description="現在キューに登録されている曲のリストを表示します。")
    @require_voice
    async def queue(self, ctx):
        view = QueuesView(self.now[ctx.guild.id], ctx.author.id, "queues")
        await ctx.reply(
            embed=view.make_embed(),
            view=view
        )


def setup(bot):
    bot.add_cog(MusicNormal(bot))
