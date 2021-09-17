# RT.cogs.music - Normal

from typing import Dict

from discord.ext import commands, easy
import discord

from rtlib.slash import Option
from rtlib import componesy
from functools import wraps

from .views import (
    QueuesView, PlaylistView, AddToPlaylist, PlaylistSelect
)
from .music_player import MusicPlayer
from .data_manager import DataManager
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

    def make_npview(self, musics: list):
        view = easy.View("NowPlayingView")

        async def on_addto_playlist(_, __, interaction):
            playlists = await self.get_playlists(
                interaction.user.id
            )
            if playlists:
                await interaction.response.send_message(
                    "どのプレイリストに曲を追加しますか？", ephemeral=True,
                    view=AddToPlaylist(self, musics, playlists)
                )
            else:
                await interaction.response.send_message(
                    {"ja": "あなたはプレイリストを作っていません。",
                     "en": "You don't have a playlist."}, ephemeral=True
                )

        view.add_item(
            "button", on_addto_playlist,
            label="プレイリストに追加する。",
            emoji="⏺"
        )
        return view()

    async def search_result_select(
        self, select: discord.ui.Select, interaction: discord.Interaction
    ):
        # 検索結果を選択された際に呼び出される関数です。
        ctx = await self.bot.get_context(interaction.message)
        ctx.reply = interaction.response.edit_message
        ctx.author = interaction.user
        ctx.interaction = interaction
        ctx.selected = True
        await self.play(ctx, song=select.values[0])

    @commands.command(
        slash_command=True,
        description="ボイスチャンネルでYouTube,ニコニコ動画,SoundCloudのどれかを再生します。"
    )
    async def play(
        self, ctx, *,
        song: Option(str, "song", "再生したい曲のURLまたは検索ワードです。"),
        datas: list = None
    ):
        if ctx.guild.id not in self.now:
            # もし接続していないなら接続をする。
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
                self.now[ctx.guild.id] = MusicPlayer(self, ctx.guild)
            else:
                return await ctx.reply(
                    content={
                        "ja": "先にボイスチャンネルに接続してください。",
                        "en": "You must connect to voice channel."
                    }
                )

        # もしdatasを指定されないなら音楽を取得する。
        # datasがしていされるというのはプレイリストから再生する際に呼ばれるから。
        i = 0
        if datas is None:
            # 入力中を表示する。
            if hasattr(ctx, "interaction"):
                kwargs = {"content": self.NOW_LOADING}
                if hasattr(ctx, "selected"):
                    kwargs["view"] = None
                await ctx.reply(**kwargs)
                ctx.reply = ctx.interaction.edit_original_message
            else:
                await ctx.trigger_typing()

            # 音楽を取得する。
            datas = await get_music(
                song, ctx.author, self.bot.loop, client=self.bot.session
            )

            if isinstance(datas, list):
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
                # 800個キューに追加されたらもう追加できないと表示する。
                ext = (
                    "\nですが、RTは800までしかキューを覚えることができないので800個までしか登録はされていません。",
                    "\nBut RT can only remember up to 800 cues, so only up to 800 cues were added."
                )
                break

        if i > 1:
            added = (
                "またいくつかの曲をキューに追加しました。",
                "And I added musics to queue."
            )
        else:
            added = ("", "")

        # 再生をする。
        if await self.now[ctx.guild.id].play():
            await ctx.reply(
                content={
                    "ja": f"▶️ 再生します。\n{added[0]}",
                    "en": f"▶️ Playing!\n{added[1]}"
                },
                embed=self.now[ctx.guild.id].embed(),
                view=self.make_npview(datas[:1])
            )
        else:
            length = f" Now:{self.now[ctx.guild.id].length}"
            await ctx.reply(
                content={
                    "ja": "💽 キューに追加しました。" + length + ext[0],
                    "en": "💽 Added to queues." + length + ext[1]
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
            await ctx.reply(
                embed=embed, view=self.make_npview(
                    self.now[ctx.guild.id].queues[:1]
                )
            )
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
            {"ja": f"🔁 {'ループをONにしました。' if onoff else 'ループをOFFにしました。'}",
             "en": f"🔁 {'Loop enabled!' if onoff else 'Loop disabled!'}"}
        )

    @commands.command(slash_command=True, description="曲を一時停止または再生を再開します。")
    async def pause(self, ctx):
        play = self.now[ctx.guild.id].pause()
        await ctx.reply("▶️ Resumed!" if play else '⏸ Paused!')

    @commands.command(slash_command=True, description="現在キューに登録されている曲のリストを表示します。")
    @require_voice
    async def queue(self, ctx):
        if self.now[ctx.guild.id].length > 1:
            view = QueuesView(self.now[ctx.guild.id], ctx.author, "queues")
            await ctx.reply(
                embed=view.make_embed(self.bot.colors["queue"]),
                view=view
            )
        else:
            await ctx.reply(
                {"ja": "キューはありません。",
                 "en": "There is no queue."}
            )

    @commands.command(
        slash_command=True, description="キューをシャッフルします。",
        aliases=["sf", "シャッフル", "ランダム", "しゃっふる"]
    )
    @require_voice
    @require_dj
    async def shuffle(self, ctx):
        self.now[ctx.guild.id].shuffle()
        await ctx.reply(
            {"ja": "🔀 シャッフルしました。",
             "en": "🔀 Shuffled!"}
        )

    @commands.command(slash_command=True, description="キューをすべて削除します。")
    @require_voice
    @require_dj
    async def clear(self, ctx):
        self.now[ctx.guild.id].clear()
        await ctx.reply(
            {"ja": "🌀 キューを全て削除しました。",
             "en": "🌀 Cleared!"}
        )

    @commands.group(slash_command=True, description="プレイリスト")
    async def playlist(self, ctx):
        if not ctx.invoked_subcommand:
            await self.show(ctx)

    @playlist.command(
        description="プレイリストにある曲を表示します。また削除、キューへの追加も可能です。"
    )
    async def show(self, ctx):
        if (lists := await self.get_playlists(ctx.author.id)):
            await ctx.reply(
                {"ja": "プレイリストを選んでください。",
                 "en": "Please choose playlist."},
                view=PlaylistView(lists, self)
            )
        else:
            await ctx.reply("あなたはプレイリストを作っていません。")

    @playlist.command(description="プレイリストを作成します。")
    async def create(self, ctx, *, name: Option(str, "name", "プレイリストの名前です。")):
        try:
            await self.make_playlist(ctx.author.id, name)
        except ValueError:
            await ctx.reply(
                {"ja": "そのプレイリストは既に存在します。",
                 "en": "The playlist already exists."}
            )
        except OverflowError:
            await ctx.reply(
                {"ja": "これ以上プレイリストは作ることができません。",
                 "en": "I can't make playlist more over 10."}
            )
        else:
            await ctx.reply("Ok")

    @playlist.command(description="プレイリストを削除します。")
    async def delete(self, ctx, *, name: Option(str, "name", "プレイリストの名前です。")):
        try:
            await self.delete_playlist(ctx.author.id, name)
        except ValueError:
            await ctx.reply(
                {"ja": "そのプレイリストが見つかりませんでした。",
                 "en": "The playlist is not found."}
            )
        else:
            await ctx.reply("Ok")

    DONT_HAVE_PLAYLIST = {
        "ja": "プレイリストがないので追加できません。",
        "en": "You must have a playlist."
    }

    @playlist.command(description="プレイリストに曲を追加します。")
    async def add(
        self, ctx, *, url: Option(
            str, "url", "追加する曲のURLです。"
        )
    ):
        # プレイリストを取得する。
        if (playlists := await self.get_playlists(ctx.author.id)):
            # URLチェックをする。
            if not url.startswith(("https://", "http://")):
                return await ctx.reply(
                    {"ja": "URLである必要があります。",
                     "en": "Is it url?"}
                )

            # 入力中または検索中を表示する。
            if hasattr(ctx, "interaction"):
                await ctx.reply(self.NOW_LOADING)
                ctx.reply = ctx.interaction.edit_original_message
            else:
                await ctx.trigger_typing()

            # 音楽を取得する。
            datas = await get_music(
                url, ctx.author, self.bot.loop, client=self.bot.session
            )
            if not isinstance(datas, list):
                datas = [datas]

            await ctx.reply(
                content={
                    "ja": "どのプレイリストに追加しますか？",
                    "en": "To which playlist do you want to add?"
                },
                view=AddToPlaylist(self, datas, playlists)
            )
        else:
            await ctx.reply(self.DONT_HAVE_PLAYLIST)

    @playlist.command("play", description="プレイリストから音楽を再生します。")
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def play_(self, ctx):
        if (playlists := await self.get_playlists(ctx.author.id)):

            async def play_from_list(select, interaction):
                if interaction.user.id == ctx.author.id:
                    await interaction.response.edit_message(
                        content=self.NOW_LOADING, view=None
                    )
                    ctx.author = interaction.user
                    ctx.interaction = interaction
                    ctx.reply = interaction.edit_original_message
                    await self.play(
                        ctx, song="",
                        datas=PlaylistSelect.make_music_data_from_playlist(
                            (
                                await self.read_playlists(
                                    interaction.user.id, select.values[0]
                                )
                            )[select.values[0]], ctx.author
                        )
                    )
                else:
                    await interaction.response.send_message(
                        content={
                            "ja": "あなたはこのプレイリストの所有者ではありません。",
                            "en": "You do not own this playlist."
                        }
                    )

            view = easy.View("PlayMusicFromPlaylist")
            view.add_item(
                discord.ui.Select, play_from_list,
                options=[
                    discord.SelectOption(label=name, value=name)
                    for name in playlists
                ]
            )
            await ctx.reply(
                {"ja": "プレイリストを選択してください。",
                 "en": "Please select a playlist."},
                view=view
            )
        else:
            await ctx.reply(self.DONT_HAVE_PLAYLIST)

    def cog_unload(self):
        for guild_id in self.now:
            self.now[guild_id].queues = self.now[guild_id].queues[:1]
            self.now[guild_id].stop()
            self.bot.loop.create_task(self.now[guild_id].vc.disconnect())


def setup(bot):
    bot.add_cog(MusicNormal(bot))
