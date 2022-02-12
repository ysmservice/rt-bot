# RT - Music

from __future__ import annotations

from typing import TypeVar, Callable, Literal, Union, Optional, Any

from functools import wraps

import discord.ext.commands as commands
import discord

from rtlib.slash import loading, UnionContext, Context
from rtutil.views import TimeoutView
from rtlib import RT, Table, sendKwargs

from .views import (
    PLAYLIST_SELECT, Confirmation, MusicSelect, Queues, AddMusicPlaylistSelect,
    ShowPlaylistSelect, PlayPlaylistSelect, AddMusicPlaylistView
)
from .player import Player, NotAddedReason, LoopMode
from .music import MusicDict, Music
from .playlist import Playlist


IM_MACHINE = "私は夢見るマシーンです。"
class EMOJIS:
    start = "▶️"
    pause = "⏸"
    stop = "⏹"
    skip = "⏭"
    reversed_skip = "⏮"
    queued = "#️⃣"
    removed = "🌀"
    all_loop = "🔁"
    one_loop = "🔂"
    shuffle = "🔀"


class DJData(Table):
    __allocation__ = "GuildID"
    dj: int


class UserMusics(Table):
    __allocation__ = "UserID"
    playlists: dict[str, list[MusicDict]]


DecoT = TypeVar("DecoT")
def check(
    headding: dict[str, str], check_state: bool = True, check_dj: bool = True
) -> Callable[[DecoT], DecoT]:
    """音楽再生コマンドにつけるデコレータです。
    権限の確認等を行います。また、見出しをつけます。"""
    def decorator(func):
        original = func.callback
        @commands.cooldown(1, 3, commands.BucketType.user)
        @wraps(func._callback)
        async def new(self: MusicCog, ctx: commands.Context, *args, **kwargs):
            if not check_state:
                return await original(self, ctx, *args, **kwargs)

            if ctx.message.author.voice is None:
                await ctx.reply(
                    {"ja": "ボイスチャンネルに接続してください。",
                     "en": "You must be connected to a voice channel."}
                )
            elif ctx.guild.voice_client is None:
                return await ctx.reply(
                    {
                        "ja": "自分ボイスチャンネルに参加していないです。音楽再生をしてください。\n"
                            "*P.S.* もしボイスチャンネルにいるのにこうなる場合は`rt!disconnect on`を実行してください。",
                        "en": "I have not joined my own voice channel. Please play the music.\n"
                            "*P.S.* If this happens while you are on the voice channel, run `rt!disconnect on`."
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
                view = Confirmation(original(self, ctx, *args, **kwargs), members, ctx)
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
                return await original(self, ctx, *args, **kwargs)
        if "headding" not in func.extras:
            func.extras["headding"] = headding
        func._callback = new
        return func
    return decorator


class MusicCog(commands.Cog, name="Music"):

    EMOJIS = EMOJIS

    def __init__(self, bot: RT):
        self.bot = bot
        self.now: dict[int, Player] = {}
        self.dj, self.data = DJData(self.bot), UserMusics(self.bot)

    def print(self, *args, **kwargs):
        "デバッグ用とかっこつけるためのprintです。"
        return self.bot.print("[MusicPlayer]", *args, **kwargs)

    def max(self, member: Union[discord.Member, discord.Guild, int] = None) -> int:
        "最大曲数を取得します。"
        return 800 # TODO: 課金要素を作ったら課金している人のみ1600にする。

    def get_player(self, guild_id: int) -> Optional[Player]:
        "指定されたGuildIDの音楽プレイヤーを返します。ただのエイリアス"
        return self.now.get(guild_id)

    @check({"ja": "音楽再生をします。", "en": "Play music"}, False)
    @commands.command(aliases=["p", "再生"])
    async def play(self, ctx: UnionContext, *, song: str = discord.SlashOption(
        "song", PDETAILS := "曲のURLまたは検索ワード｜Song url or search term"
    )):
        await loading(ctx)
        await self._play(ctx, song)

    def _get_status(self, status: Union[Exception, NotAddedReason]) -> Union[dict[str, str], str]:
        # 渡されたステータスから適切な返信を選びます。
        if isinstance(status, Exception):
            return {
                "ja": "楽曲の読み込みに失敗してしまいました。"
                    + (code := f"\ncode: `{status.__class__.__name__} - {status}`"),
                "en": f"Failed to load a music.{code}"
            }
        elif status == NotAddedReason.list_very_many:
            return {
                "ja": "リストが大きすぎたため後半の曲は追加されていません。",
                "en": "The second half of the song has not been added because the list was too large."
            }
        elif status == NotAddedReason.queue_many:
            return {
                "ja": "キューが満タンなため恐らくいくつかの曲が追加されていません。",
                "en": "Some songs have not been added, probably because the queue is full."
            }
        else:
            # ここは呼ばれたらおかしい。
            return IM_MACHINE

    async def _play(self, ctx: UnionContext, url: Union[str, Music, list[Music]]):
        # 曲を再生するための関数です。playコマンドの実装であり再呼び出しをする際の都合上別に分けています。
        assert ctx.guild is not None, "サーバーでなければ実行できません。"

        # 接続していない場合は接続してPlayerを準備する。
        if ctx.guild.id not in self.now:
            self.now[ctx.guild.id] = Player(
                self, ctx.guild, await ctx.author.voice.channel.connect()
            )
            self.now[ctx.guild.id].channel = ctx.channel

        status: Any = {}
        if isinstance(url, str):
            # 曲を読み込みむ。
            if (status := await self.now[ctx.guild.id].add_from_url(
                ctx.author, url
            )) is not None:
                if isinstance(status, list):
                    # リストの場合は検索結果のため選んでもらう。
                    view = TimeoutView()
                    view.add_item(MusicSelect(
                        status, lambda select, interaction: self.bot.loop.create_task(
                            self._play(
                                Context(
                                    ctx.bot, interaction, ctx.command,
                                    ctx.message.content, False, True
                                ), status[int(select.values[0])]
                            )
                        )
                    ))
                    view.message = await ctx.reply(
                        content={
                            "ja": "検索結果が複数あるので選んでください。",
                            "en": "There are multiple search results to choose from."
                        }, view=view
                    )
                    return
                else:
                    # もし何かしら発生したのなら警告を入れる。
                    status = self._get_status(status)
        elif isinstance(url, list):
            # `rt!playlist play`によってplayされた際にはurlにlist[Music]が入るのでここが実行される。
            for music in url:
                self.now[ctx.guild.id].add(music)
            ctx.reply_edit = True
        else:
            # 検索結果から選ばれた曲をキューに追加する。
            self.now[ctx.guild.id].add(url)

        # statusがもし空じゃないのなら危険と追記する。
        if status:
            status["ja"] = f"⚠️ 警告\n{status['ja']}\n"
            status["en"] = f"⚠️ Warnings\n{status['en']}\n"
        else:
            status = {"ja": "", "en": ""}

        if "code" in status["ja"]:
            return await ctx.reply(status)

        # 返信またはそれに加えて音楽再生の開始をする。
        if self.now[ctx.guild.id].vc.is_playing():
            await ctx.reply(
                content={
                    "ja": f"{status.get('ja', '')}{EMOJIS.queued} 曲をキューに追加しました。",
                    "en": f"{status.get('en', '')}{EMOJIS.queued} Queued"
                }, embed=None, view=None
            )
        else:
            assert (now := self.now[ctx.guild.id].now) is not None, IM_MACHINE
            view = AddMusicPlaylistView(now, self)
            view.message = await ctx.reply(
                content={
                    "ja": f"{status.get('ja', '')}{EMOJIS.start} 音楽再生を開始します。",
                    "en": f"{status.get('en', '')}{EMOJIS.start} Starting music player..."
                }, embed=now.make_embed(), view=view
            )
            await self.now[ctx.guild.id].play()

    @check({"ja": "切断をします。", "en": "Disconnect"})
    @commands.command(aliases=["leave", "stop", "dis", "bye", "切断"])
    async def disconnect(self, ctx: UnionContext, force: bool = False):
        try:
            await self.now[ctx.guild.id].disconnect(force=force)
        except KeyError:
            if ctx.guild.voice_client is not None:
                await ctx.guild.voice_client.disconnect(force=force)
        await ctx.reply(f"{EMOJIS.stop} Bye!")

    @check({"ja": "スキップをします。", "en": "Skip"})
    @commands.command(aliases=["s", "スキップ"])
    async def skip(self, ctx: UnionContext):
        self.now[ctx.guild.id].skip()
        await ctx.reply(f"{EMOJIS.skip} Skipped")

    @check({"ja": "ループの設定をします。", "en": "Toggle loop"})
    @commands.command(aliases=["rp", "loop", "ループ"])
    async def repeate(self, ctx: UnionContext, mode: Literal["none", "all", "one", "auto"] = "auto"):
        now = self.now[ctx.guild.id].loop() if mode == "auto" \
            else self.now[ctx.guild.id].loop(getattr(LoopMode, mode))
        if now == LoopMode.none:
            content = {
                "ja": "🛑 リピート再生を無効にしました。",
                "en": "🛑 Disabled repeate."
            }
        elif now == LoopMode.all:
            content = {
                "ja": f"{EMOJIS.all_loop} 全曲リピート再生が有効になりました。",
                "en": f"{EMOJIS.all_loop} All song repeates are now enabled."
            }
        else:
            content = {
                "ja": f"{EMOJIS.one_loop} 一曲リピート再生が有効になりました。",
                "en": f"{EMOJIS.one_loop} One-song repeat playback is now enabled."
            }
        await ctx.reply(content)

    @check({"ja": "シャッフルします。", "en": "Shuffle"})
    @commands.command(aliases=["sfl", "シャッフル"])
    async def shuffle(self, ctx: UnionContext):
        self.now[ctx.guild.id].shuffle()
        await ctx.reply(f"{EMOJIS.shuffle} Shuffled")

    @check({"ja": "一時停止します。", "en": "Pause"})
    @commands.command(aliases=["ps", "resume", "一時停止"])
    async def pause(self, ctx: UnionContext):
        await ctx.reply(
            f"{EMOJIS.start} Resumed"
            if self.now[ctx.guild.id].pause() else
            f"{EMOJIS.pause} Paused"
        )

    @check({"ja": "音量を変更します。", "en": "Change volume"})
    @commands.command(aliases=["vol", "音量"])
    async def volume(self, ctx: UnionContext, volume: Optional[float] = None):
        if volume is None:
            await ctx.reply(f"Now volume: {self.now[ctx.guild.id].volume}")
        else:
            assert 0 <= volume <= 100, "音量は0から100の間である必要があります。"
            self.now[ctx.guild.id].volume = volume
            await ctx.reply("🔈 Changed")

    @check({"ja": "現在再生中の曲を表示します。", "en": "Displays the currently playing music."})
    @commands.command(aliases=["現在"])
    async def now(self, ctx: UnionContext):
        view = AddMusicPlaylistView(self.now[ctx.guild.id].now, self)
        view.message = await ctx.reply(
            embed=self.now[ctx.guild.id].now.make_embed(True), view=view
        )

    @check({"ja": "現在登録されているキューを表示します。", "en": "Displays currently queues registered."})
    @commands.command(aliases=["キュー", "qs"])
    async def queues(self, ctx: UnionContext):
        view = Queues(self, self.now[ctx.guild.id].queues)
        view.message = await ctx.reply(embed=view.data[0], view=view)

    @check({"ja": "プレイリスト", "en": "Playlist"}, False)
    @commands.group(aliases=["pl", "プレイリスト", "再生リスト"])
    async def playlist(self, ctx: UnionContext):
        if not ctx.invoked_subcommand:
            self.assert_playlist(ctx.author.id)
            await ctx.reply(embed=discord.Embed(
                title={
                    "ja": "あなたのプレイリスト",
                    "en": "Playlists"
                }, description="\n".join(
                    f"・{name}" for name in list(self.data[ctx.author.id].playlists.keys())
                ), color=self.bot.Colors.normal
            ))

    def assert_playlist(self, author_id: int):
        "プレイリストを作っているかのチェックをします。"
        assert "playlists" in self.data[author_id], {
            "ja": "現在あなたはプレイリストを所有していません。\n`rt!playlist create <名前>`で作成可能です。",
            "en": "Currently, You don't have any playlists.\n`rt!playlist create <NAME>` to create a playlist."
        }

    def get_playlist(self, author_id: int, name: str) -> Playlist:
        "Playlistを取得します。"
        self.assert_playlist(author_id)
        assert name in self.data[author_id].playlists, "そのプレイリストが見つかりませんでした。"
        return Playlist(self.data[author_id].playlists[name], self.max(author_id))

    @playlist.command(
        aliases=["c", "new", "作成"], description="プレイリストを新規作成します。｜Create a playlist"
    )
    async def create(self, ctx: UnionContext, *, name: str = discord.SlashOption(
        "name", PN := "プレイリストの名前です。｜Playlist name"
    )):
        if "playlists" not in self.data[ctx.author.id]:
            self.data[ctx.author.id].playlists = {}
        assert len(self.data[ctx.author.id].playlists) < 10, {
            "ja": "これ以上作れません。", "en": "You can't create playlist more than 10."
        }
        if name in self.data[ctx.author.id].playlists:
            await ctx.reply({
                "ja": "既にその名前のプレイリストは存在します。",
                "en": "That name playlist is already exists."
            })
        else:
            self.data[ctx.author.id].playlists[name] = []
            await ctx.reply("Ok")

    @playlist.command(
        aliases=["rm", "del", "削除"], description="プレイリストを削除します。｜Delete playlist"
    )
    async def delete(self, ctx: UnionContext, *, name: str = discord.SlashOption("name", PN)):
        self.get_playlist(ctx.author.id, name)
        del self.data[ctx.author.id].playlists[name]
        await ctx.reply("Ok")

    @playlist.command(aliases=["a", "追加"])
    async def add(self, ctx: UnionContext, *, url: str = discord.SlashOption("url", PDETAILS)):
        self.assert_playlist(ctx.author.id)
        assert self.data[ctx.author.id].playlists, "プレイリストがまだ作られていません。"
        view = TimeoutView()
        view.add_item(select:=AddMusicPlaylistSelect(
            self.data[ctx.author.id].playlists, self
        ))
        select.song = url
        view.message = await ctx.reply(
            PLAYLIST_SELECT,
            view=view, **sendKwargs(ctx, ephemeral=True)
        )

    async def _run_playlist_command(self, ctx, name, content=PLAYLIST_SELECT):
        self.assert_playlist(ctx.author.id)
        view = TimeoutView()
        view.add_item(globals()[name](self.data[ctx.author.id].playlists, self))
        view.message = await ctx.reply(content, view=view, **sendKwargs(ctx, ephemeral=True))

    @playlist.command(aliases=["s", "表示"])
    async def show(self, ctx: UnionContext):
        await self._run_playlist_command(ctx, "ShowPlaylistSelect")

    @playlist.command("play")
    async def playlist_play(self, ctx: UnionContext):
        await self._run_playlist_command(ctx, "PlayPlaylistSelect")

    @check({"ja": "DJの設定をします。", "en": "Setting dj"}, False)
    @commands.command(aliases=["だーじぇー"])
    async def dj(self, ctx: UnionContext, *, role: Union[discord.Role, bool]):
        if role is False:
            if "dj" in self.dj[ctx.guild.id]:
                del self.dj[ctx.guild.id]
        else:
            self.dj[ctx.giuld.id].dj = role.id
        await ctx.reply("Ok")

    def cog_unload(self):
        # コグがアンロードされた際にもし使用されてる音楽プレイヤーがあれば終了する。
        for player in list(self.now.values()):
            self.bot.loop.create_task(
                player.disconnect(
                    {"ja": "すみませんが再起動または音楽プレイヤーの更新のため音楽再生を終了します。",
                     "en": "Sorry, music playback will be terminated due to reboot or music player update."}
                ), name=f"{player}.disconnect"
            )

    def remove_player(self, guild_id: int):
        "音楽プレイヤーを削除するだけの関数です。"
        del self.now[guild_id]


def setup(bot):
    bot.add_cog(MusicCog(bot))