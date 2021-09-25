# RT.cogs.music - Normal

from typing import Dict

from discord.ext import commands, tasks, easy
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
        self.check_timeout.start()
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
        description="ボイスチャンネルでYouTube,ニコニコ動画,SoundCloudのどれかを再生します。",
        extras={
            "headding": {
                "ja": "音楽を再生します。",
                "en": "Play music."
            }, "parent": "Music"
        }
    )
    async def play(
        self, ctx, *,
        song: Option(str, "song", "再生したい曲のURLまたは検索ワードです。"),
        datas: list = None
    ):
        """!lang ja
        --------
        音楽を再生します。    
        YouTube/SoundCloud/ニコニコ動画に対応しています。  
        読み上げと同時に使用することはできないので、もし読み上げと同時に使用したい人はサブのりつちゃんを入れましょう。  
        りつちゃんについてはRTのサポートサーバー(`rt!info`から確認が可能)にてお知らせします。

        Notes
        -----
        もしURLではないものを入力した場合は検索が行われます。  
        YouTubeの再生リストからの再生に対応しています。  
        (SoundCloud/ニコニコ動画上の再生リストからの再生は後日対応予定です。)  
        そして音楽再生コマンドはスラッシュコマンドに対応しています。  
        もし再生中に再生しようとした場合はキューに追加され順番が来たら再生されます。  
        ※キューというのは再生予定の曲のリストのことです。

        Warnings
        --------
        YouTubeを再生する機能はご存じの通りGroovyやRythmがGoogleに停止通知を受けてサービス終了をしていることからいつか廃止します。

        Parameters
        ----------
        song : str
            再生したい曲のURLまたは検索ワードです。  
            YouTubeの再生リストのURLが渡された場合はその再生リストを全て再生します。

        Examples
        --------
        `rt!play https://www.youtube.com/watch?v=Th-Z6le3bHA`
        `rt!play Never Gonna Give You Up`
        `/play 白日`

        !lang en
        --------
        Play music.
        It supports YouTube/SoundCloud/NicoNico video.

        Notes
        -----
        If you enter something that is not a URL, a search is performed.
        It supports playback from YouTube playlists.
        (Playing from the playlist on SoundCloud/NicoNico video will be available at a later date.)
        And the music playback command corresponds to the slash command.
        If you try to play it during playback, it will be added to the queue and will play back when it is in order.

        Warnings
        --------
        As you know, Groovy and Rythm shut down their services after Google notified them of their suspension, so we'll eventually phase them out.

        Parameters
        ----------
        song: str
            URL or search word of the song you want to play.
            If you're given a URL for a YouTube playlist, play it all.

        Examples
        --------
        `rt!play https://www.youtube.com/watch?v=Th-Z6le3bHA`
        `rt!play Never Gonna Give You Up`
        `/play We are number one`"""
        if ctx.guild.id not in self.now:
            # もし接続していないなら接続をする。
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
                self.now[ctx.guild.id] = MusicPlayer(self, ctx.guild, ctx.channel)
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
            try:
                datas = await get_music(
                    song, ctx.author, self.bot.loop, client=self.bot.session
                )
            except KeyError:
                return await ctx.reply(
                    content={
                        "ja": "その音楽の情報を取り出せませんでした。",
                        "en": "I couldn't get the music information out."
                    }
                )
            except Exception as e:
                return await ctx.reply(
                    content={
                        "ja": f"何かエラーが起きたため音楽を再生することができませんでした。\ncode:`{e}`",
                        "en": f"Something went wrong.\ncode:`{e}`"
                    }
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
        aliases=["dis", "leave", "切断", "bye", "せつだん"], extras={
            "headding": {
                "ja": "音楽再生を終了し切断をします。",
                "en": "Stop playing music and disconnect from vc."
            }, "parent": "Music"
        }
    )
    @require_voice
    @require_dj
    async def disconnect(self, ctx):
        """!lang ja
        --------
        音楽再生を終了してボイスチャンネルから切断をします。

        Aliases
        -------
        dis, leave, bye, せつだん, 切断

        !lang en
        --------
        Ends music playback and disconnects from the voice channel.

        Aliases
        -------
        dis, leave, bye"""
        if ctx.guild.voice_client:
            await ctx.guild.voice_client.disconnect()
        if ctx.guild.id in self.now:
            del self.now[ctx.guild.id]
        await ctx.reply(
            {"ja": "⏹ 切断しました。",
             "en": "⏹ Disconnected!"}
        )

    @commands.command(
        slash_command=True, description="現在再生している曲の情報を表示します。",
        aliases=["np", "nowplaying", "曲"], extras={
            "headding": {
                "ja": "現在再生している曲の情報を表示します。",
                "en": "Show you music details."
            }, "parent": "Music"
        }
    )
    @require_voice
    async def now(self, ctx):
        """!lang ja
        --------
        現在再生している音楽の情報と経過時間を表示します。  
        また、プレイリストに追加するボタンもあります。

        Aliases
        -------
        np, nowplaying, 曲

        !lang en
        --------
        Show you music playing details.  
        And it has "Add to playlist" button.

        Aliases
        -------
        np, nowplaying"""
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

    @commands.command(
        slash_command=True, description="曲をスキップします。",
        aliases=["s", "スキップ", "すきっぷ"], extras={
            "headding": {
                "ja": "曲をスキップします。", "en": "Do skipping."
            }, "parent": "Music"
        }
    )
    @require_voice
    @require_dj
    async def skip(self, ctx):
        """!lang ja
        --------
        現在再生している曲を停止して次の曲を再生します。

        Aliases
        -------
        s, スキップ, すきっぷ

        !lang en
        --------
        Skip music.

        Aliases
        -------
        s"""
        self.now[ctx.guild.id].skip()
        await ctx.reply(
            {"ja": "⏭ スキップします。",
             "en": "⏭ Skipped!"}
        )

    @commands.command(
        slash_command=True, description="曲をループさせます。",
        aliases=["l", "ループ"], extras={
            "headding": {
                "ja": "曲をループさせます。", "en": "Loop the song."
            }, "parent": "Music"
        }
    )
    async def loop(self, ctx):
        """!lang ja
        --------
        現在再生している曲をループさせます。  
        またループを解除します。

        Aliases
        -------
        l, ループ

        !lang en
        --------
        Loop the song or disable loop.

        Aliases
        -------
        l"""
        onoff = self.now[ctx.guild.id].loop()
        await ctx.reply(
            {"ja": f"🔁 {'ループをONにしました。' if onoff else 'ループをOFFにしました。'}",
             "en": f"🔁 {'Loop enabled!' if onoff else 'Loop disabled!'}"}
        )

    @commands.command(
        slash_command=True, description="曲を一時停止または再生を再開します。",
        aliases=["p", "一時停止", "ポーズ", "ぽーず", "いちじていし"], extras={
            "headding": {
                "ja": "曲を一時停止します。",
                "en": "Pause the song."
            }, "parent": "Music"
        }
    )
    async def pause(self, ctx):
        """!lang ja
        --------
        曲を一時停止/再開します。

        Aliases
        -------
        p, 一時停止, ポーズ, ぽーず, いちじていし

        !lang en
        --------
        Puase the song or resume the song.

        Aliases
        -------
        p"""
        play = self.now[ctx.guild.id].pause()
        await ctx.reply("▶️ Resumed!" if play else '⏸ Paused!')

    @commands.command(
        slash_command=True, description="現在キューに登録されている曲のリストを表示します。",
        aliases=["q", "キュー", "きゅー", "再生予定"], extras={
            "headding": {
                "ja": "キューにある曲を表示します。",
                "en": "Displays a list of songs currently queued."
            }, "parent": "Music"
        }
    )
    @require_voice
    async def queue(self, ctx):
        """!lang ja
        --------
        現在キューに登録されている曲のリストを表示します。  
        また他に聞いている人がいないまたはDJ役職を持っている人はキューの削除を行うことができます。  
        そしてキューにある曲をプレイリストに追加することもできます。

        Notes
        -----
        キューというのは再生予定の曲のリストのことです。

        Aliases
        -------
        q, キュー, きゅー, 再生予定

        !lang en
        --------
        Displays a list of songs currently queued.
        You can also delete a queue if no one else is listening or you have a DJ role.
        You can also add songs from the queue to your playlist.

        Notes
        -----
        A queue is a list of songs to be played.

        Aliases
        -------
        q"""
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
        aliases=["sf", "シャッフル", "ランダム", "しゃっふる"], extras={
            "headding": {
                "ja": "キューをシャッフルします。", "en": "Shuffle queues"
            }, "parent": "Music"
        }
    )
    @require_voice
    @require_dj
    async def shuffle(self, ctx):
        """!lang ja
        --------
        キューをシャッフルします。

        Aliases
        -------
        sf, シャッフル, しゃっふる, ランダム

        !lang en
        --------
        Shuffle the queues.

        Aliases
        -------
        sf"""
        self.now[ctx.guild.id].shuffle()
        await ctx.reply(
            {"ja": "🔀 シャッフルしました。",
             "en": "🔀 Shuffled!"}
        )

    @commands.command(
        slash_command=True, description="キューをすべて削除します。",
        aliases=[
            "c", "reset", "エクスプロージョン", "クリア",
            "くりあ", "リセット", "りせっと"
        ], extras={
            "headding": {
                "ja": "キューにある曲を全て削除します。",
                "en": "Clear the queues."
            }, "parent": "Music"
        }
    )
    @require_voice
    @require_dj
    async def clear(self, ctx):
        """!lang ja
        --------
        キューにある曲をすべて削除します。

        Aliases
        -------
        c, reset, クリア, くりあ, リセット, りせっと, エクスプロージョン

        !lang en
        --------
        Clear the queues.

        Aliases
        -------
        c, reset"""
        self.now[ctx.guild.id].clear()
        await ctx.reply(
            {"ja": "🌀 キューを全て削除しました。",
             "en": "🌀 Cleared!"}
        )

    @commands.group(
        slash_command=True, description="プレイリスト", extras={
            "headding": {
                "ja": "プレイリスト機能", "en": "Playlist"
            }, "parent": "Music"
        }, aliases=["pl", "ぷれいりすと", "プレイリスト", "再生リスト"]
    )
    async def playlist(self, ctx):
        """!lang ja
        --------
        プレイリスト機能で好きな曲のリストを十個まで作成することが可能です。

        Aliases
        -------
        pl, ぷれいりすと, プレイリスト, 再生リスト

        !lang en
        --------
        The playlist feature lets you create a list of up to ten songs you like.

        Aliases
        -------
        pl"""
        if not ctx.invoked_subcommand:
            await self.show(ctx)

    @playlist.command(
        description="プレイリストにある曲を表示します。また削除、キューへの追加も可能です。",
        aliases=["s", "表示", "しょう", "ゆー", "ざ", "ぱすぽーと", "ぷりーず"]
    )
    async def show(self, ctx):
        """!lang ja
        --------
        プレイリストにある曲を表示します。  
        またプレイリストから曲を削除することもできます。　　
        もし音楽プレイヤーを使ってる際に実行すれば、プレイリストから曲をキューに追加することもできます。

        Aliases
        -------
        s, 表示, しょう, ゆー, ざ, ぱすぽーと, ぷりーず

        !lang en
        --------
        Displays the songs in the playlist.
        You can also delete songs from playlists.
        If you're using a music player, you can also queue songs from a playlist.

        Aliases
        -------
        s"""
        if (lists := await self.get_playlists(ctx.author.id)):
            await ctx.reply(
                {"ja": "プレイリストを選んでください。",
                 "en": "Please choose playlist."},
                view=PlaylistView(lists, self)
            )
        else:
            await ctx.reply("あなたはプレイリストを作っていません。")

    @playlist.command(
        description="プレイリストを作成します。", aliases=[
            "c", "make", "っていうやつあるよね", "作成", "つくる", "作る"
        ]
    )
    async def create(self, ctx, *, name: Option(str, "name", "プレイリストの名前です。")):
        """!lang ja
        --------
        プレイリストを作成します。

        Parameters
        ----------
        name : str
            作成するプレイリストの名前です。

        Examples
        --------
        `rt!playlist create 淫夢MAD`

        Aliases
        -------
        c, make, ってやつあるよね, 作成, つくる, 作る

        !lang en
        --------
        Create the playlist.

        Parameters
        ----------
        name : str
            Playlist name.

        Examples
        --------
        `rt!playlist create YTPMV`

        Aliases
        -------
        c, make"""
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

    @playlist.command(
        description="プレイリストを削除します。", aliases=[
            "del", "remove", "rm", "削除", "さくじょ"
        ]
    )
    async def delete(self, ctx, *, name: Option(str, "name", "プレイリストの名前です。")):
        """!lang ja
        --------
        プレイリストを削除します。

        Parameters
        ----------
        name : str
            削除するプレイリストの名前です。

        Examples
        --------
        `rt!playlist delete 空手部`

        Aliases
        -------
        del, remove, rm, 削除, さくじょ

        !lang en
        --------
        Delete the playlist.

        Parameters
        ----------
        name : str
            Playlist name.

        Examples
        --------
        `rt!playlist delete I love you songs`

        Aliases
        -------
        del, remove, rm"""
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

    @playlist.command(
        description="プレイリストに曲を追加します。", aliases=[
            "a", "new", "あどど", "追加"
        ]
    )
    async def add(
        self, ctx, *, url: Option(
            str, "url", "追加する曲のURLです。"
        )
    ):
        """!lang ja
        --------
        プレイリストに曲を追加します。  
        引数に追加先のプレイリストの名前がありませんが、これはコマンド実行後にメニューバーで選択するので問題はありません。

        Notes
        -----
        YouTubeの再生リストのURLを指定された場合はその再生リストにある曲全てを追加します。  
        そして追加できる曲の数は800までとなっています。

        Warnings
        --------
        YouTubeを再生する機能はご存じの通りGroovyやRythmがGoogleに停止通知を受けてサービス終了をしていることからいつか廃止します。  
        ですので追加する曲はできるだけSoundCloudやニコニコ動画にあるものにするのを推奨します。

        Parameters
        ----------
        url : str
            追加する曲のURLです。  
            YouTubeの再生リストの場合はその再生リストにある曲全てを追加します。

        Examples
        --------
        `rt!playlist add https://www.youtube.com/watch?v=I1mOeAtPkgk`

        Aliases
        -------
        a, new, あどど, 追加

        !lang en
        --------
        Adds a song to the playlist.
        The argument does not contain the name of the playlist to add to, but this is fine because it is selected in the menu bar after the command is executed.

        Notes
        -----
        If you specify a URL for a YouTube playlist, all songs in that playlist will be added.
        And you can only add up to 800 songs.

        Warnings
        --------
        As you know, Groovy and Rythm shut down their services after Google notified them of their suspension, so we'll eventually phase them out.
        Therefore, I recommend you to add the songs in SoundCloud or Niconico video as much as possible.

        Parameters
        ----------
        url : str
            The URL of the song to add.
            If it's a YouTube playlist, it adds all the songs in that playlist.

        Examples
        --------
        `rt!playlist add https://www.youtube.com/watch?v=I1mOeAtPkgk`

        Aliases
        -------
        a, new"""
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
        """!lang ja
        --------
        プレイリストにある曲を全て再生します。

        !lang en
        --------
        Play musics from playlist."""
        if (playlists := await self.get_playlists(ctx.author.id)):

            async def play_from_list(select, interaction):
                if interaction.user.id == ctx.author.id:
                    await interaction.response.edit_message(
                        content=self.NOW_LOADING, view=None
                    )
                    ctx.author = interaction.user
                    ctx.interaction = interaction
                    ctx.reply = interaction.edit_original_message
                    try:
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
                    except Exception as e:
                        await ctx.reply(content=f"何かエラーが起きました。\n`{e}`")
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

    async def wrap_error(self, coro):
        try:
            return await coro
        except Exception as e:
            if self.bot.test:
                print("Error on tts:", e)

    def shutdown_player(self, guild_id: int, reason: str, disconnect: bool = True) -> None:
        if guild_id in self.now and self.now[guild_id].voice_client.is_playing():
            self.now[guild_id].force_end = True
            self.now[guild_id].clear()
            if disconnect:
                for coro in list(map(self.wrap_error, (
                        self.now[guild_id].voice_client.disconnect(force=True),
                        self.now[guild_id].channel.send(reason)
                    )
                )):
                    self.bot.loop.create_task(coro)
            del self.now[guild_id]

    def cog_unload(self):
        self.check_timeout.cancel()
        for guild_id in self.now:
            self.shutdown_player(guild_id, "再起動のため音楽再生を終了します。")

    @commands.Cog.listener()
    async def on_voice_abandoned(self, voice_client):
        # もしメンバーがいないのに接続されているチャンネルがあるなら自動で抜け出す。
        if voice_client.guild.id in self.now:
            self.shutdown_player(
                voice_client.guild.id, "誰もいないので音楽再生を終了します。"
            )

    @tasks.loop(minutes=5)
    async def check_timeout(self):
        # 再生していないで放置されてる場合は抜ける。
        for guild_id in self.now:
            if not self.now[guild_id].first and self.now[guild_id].check_timeout():
                self.shutdown_player(
                    guild_id, "何も再生してない状態で放置されたので音楽再生を終了します。"
                )

    @commands.Cog.listener()
    async def on_voice_leave(self, member, _, __):
        # もしRTがけられたりした場合は終了する。
        if member.id == self.bot.user.id:
            self.shutdown_player(member.guild.id, "")


def setup(bot):
    bot.add_cog(MusicNormal(bot))
