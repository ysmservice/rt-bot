# RT - TTS

from __future__ import annotations

from typing import TypedDict, TypeVar, Literal, Optional, Any

from functools import wraps
from os import listdir

from discord.ext import commands, tasks
import discord

from aiofiles.os import remove

from rtlib.slash import UnionContext
from rtlib import RT, Table
from rtutil.views import TimeoutView

from .agents import OPENJTALK, AGENTS
from .voice import OUTPUT_DIRECTORY
from .manager import Manager


class RoutineData(TypedDict):
    keys: list[str]
    path: str


class TTSUserData(Table):
    __allocation__ = "UserID"
    routines: list[RoutineData]
    voice: str


class TTSGuildData(Table):
    __allocation__ = "GuildID"
    dictionary: dict[str, str]


DecoFuncT = TypeVar("DecoFuncT")
def check(func: DecoFuncT) -> DecoFuncT:
    "読み上げの設定を変更可能かどうかチェックするデコレータ"
    @wraps(func)
    async def new(self: TTSCog, ctx: UnionContext, *args, **kwargs):
        if ctx.guild.id not in self.now:
            await ctx.reply({
                "ja": "まだ読み上げを開始していません。",
                "en": "It has not yet started tts."
            })
        else:
            return await func(self, ctx, *args, **kwargs)
    return new


class SelectAgentView(TimeoutView):
    "AgentセレクトのViewです。"

    def __init__(self, cog: TTSCog, *args, **kwargs):
        self.cog = cog
        super().__init__(*args, **kwargs)

    @discord.ui.select(
        placeholder="Select agent", options=[
            discord.SelectOption(
                label=agent.name, value=agent.code,
                description=agent.details, emoji=agent.emoji
            ) for agent in AGENTS.values()
        ]
    )
    async def agent_select(self, select: discord.ui.Select, interaction: discord.Interaction):
        self.cog.user[interaction.user.id].voice = select.values[0]
        await interaction.response.send_message({"ja": "設定しました。", "en": "Ok"})


class TTSCog(commands.Cog, name="TTS"):

    RTCHAN = False

    def __init__(self, bot: RT):
        self.bot = bot

        self.user = TTSUserData(self.bot)
        self.guild = TTSGuildData(self.bot)
        self.auto_leave.start()

        self.RTCHAN = self.bot.user.id == 888635684552863774
        global OPENJTALK
        if self.RTCHAN:
            # もしりつたんの場合はOpenJTalkの場所を直接指定する。
            OPENJTALK = "/home/tasuren/opt/bin/open_jtalk"

        self.now: dict[int, Manager] = {}

    @commands.group()
    async def tts(self, ctx: UnionContext):
        if not ctx.invoked_subcommand:
            await ctx.reply({
                "ja": "使用方法が違います。", "en": "It is wrong way to use this feature."
            })

    @tts.command()
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def join(self, ctx: UnionContext):
        if ctx.guild.voice_client:
            await ctx.reply({
                "ja": "既に別のチャンネルに接続しています。",
                "en": "It is already connected to another channel."
            })
        elif ctx.author.voice is None:
            await ctx.reply({
                "ja": "ボイスチャンネルに接続してください。",
                "en": "You must be connected to a voice channel."
            })
        elif ctx.guild.id in self.bot.cogs["Music"].now:
            await ctx.reply({
                "ja": "音楽プレイヤーと同時に使うことはできません。",
                "en": "Cannot be used with a music player at the same time.\nWe are currently preparing English support for Ritsu-chan, our sub RT.\nPlease wait for it to be released."
            })
        else:
            await ctx.author.voice.channel.connect()
            self.now[ctx.guild.id] = Manager(self, ctx.guild)
            self.now[ctx.guild.id].add_channel(ctx.channel.id)
            await ctx.reply({"ja": "接続しました。", "en": "Connected!"})

    @tts.command(aliases=("l", "さようなら"))
    @check
    async def leave(self, ctx: UnionContext):
        self.clean(self.now[ctx.guild.id])
        await ctx.reply("Bye!")

    @tts.command(aliases=("v", "声", "agent"))
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def voice(self, ctx: UnionContext):
        await ctx.reply({
            "ja": "音声を選んでください。", "en": "Choose your voice."
        }, view=SelectAgentView(self))

    @tts.command(aliases=("ch", "チャンネル"))
    async def channel(self, ctx: UnionContext, mode: Literal["toggle", "list"]):
        if mode == "toggle":
            if not self.now[ctx.guild.id].remove_channel(ctx.channel.id):
                self.now[ctx.guild.id].add_channel(ctx.channel.id)
            await ctx.reply("Ok")
        else:
            await ctx.reply(embed=discord.Embed(
                title={"ja": "読み上げ対称チャンネル", "en": "TTS Target Channel"},
                description="\n".join(
                    f"・<#{channel_id}>" for channel_id in self.now[ctx.guild.id].channels
                ), color=self.bot.Colors.normal
            ))

    def _assert_dict(self, ctx: UnionContext):
        assert "dictionary" in self.guild[ctx.guild.id], {
            "ja": "まだ辞書には何も設定されていません。", "en": "Nothing has been set in the dictionary yet."
        }

    @tts.group(aliases=("dic", "dict", "辞書"))
    async def dictionary(self, ctx: UnionContext):
        if ctx.invoked_subcommand:
            await ctx.reply("Ok")
        else:
            self._assert_dict(ctx)
            await ctx.reply(embed=discord.Embed(
                title={"ja": "辞書", "en": "Dictionary"},
                description="\n".join(
                    f"{before}：{after}" for before, after in list(
                        self.guild[ctx.guild.id].dictionary.items()
                    )
                ), color=self.bot.Colors.normal
            ))

    @dictionary.command(aliases=("設定", "s"))
    async def set(self, ctx: UnionContext, before, *, after):
        if "dictionary" not in self.guild[ctx.guild.id]:
            self.guild[ctx.guild.id].dictionary = {}
        self.guild[ctx.guild.id].dictionary[before] = after

    @dictionary.command(aliases=("del", "rm", "remove", "削除"))
    async def delete(self, ctx: UnionContext, *, before):
        self._assert_dict(ctx)
        assert before in self.guild[ctx.guild.id].dictionary, {
            "ja": "そのワードは設定されていません。", "en": "The word is not set."
        }
        del self.guild[ctx.guild.id].dictionary[before]

    def _assert_routine(self, ctx: UnionContext):
        assert "routines" in self.user[ctx.author.id], {
            "ja": "まだ何もRoutineは登録されていません。", "en": "Nothing has been registered for Routine yet."
        }

    @tts.group(aliases=("ネタ", "r"))
    async def routine(self, ctx: UnionContext):
        if ctx.invoked_subcommand:
            await ctx.reply("Ok")
        else:
            self._assert_routine(ctx)
            await ctx.reply(embed=discord.Embed(
                title="Routines", description="\n".join(
                    f"・[{', '.join(routine['keys'])}]({routine['path']})"
                    for routine in self.user[ctx.author.id].routines
                )
            ))

    @routine.command("set", aliases=("s", "設定"))
    async def set_routine(self, ctx: UnionContext, *, aliases):
        assert ctx.message.attachments, {
            "ja": "音楽ファイルをアップロードしてください。", "en": "You must upload file."
        }
        if "routines" not in self.user[ctx.author.id]:
            self.user[ctx.author.id].routines = []
        assert len(self.user[ctx.author.id].routines) < 20, {
            "ja": "これ以上設定できません。", "en": "No more settings can be made."
        }
        self.user[ctx.author.id].routines.append(RoutineData(
            keys=aliases.split(","), path=ctx.message.attachments[0].url
        ))

    @routine.command("delete", aliaess=("del", "rm", "remove", "削除"))
    async def delete_routine(self, ctx: UnionContext, *, alias):
        self._assert_routine(ctx)
        for index, routine in enumerate(self.user[ctx.author.id].routines):
            if alias in routine["keys"]:
                del self.user[ctx.author.id].routines[index]
                await ctx.reply("Ok")
                break
        else:
            await ctx.reply({"ja": "d見つかりませんでした。", "en": "Not found"})

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild.id in self.now \
                and self.now[message.guild.id].check_channel(message.channel.id):
            await self.now[message.guild.id].add(message)

    @commands.Cog.listener()
    async def on_voice_abandoned(self, voice_client: discord.VoiceClient):
        # 一人ぼっちになったのなら切断する。
        if voice_client.guild.id in self.now:
            self.clean(self.now[voice_client.guild.id], {
                "ja": "一人ぼっちになったので切断しました。", "en": "I was alone, so I disconnected."
            })

    @tasks.loop(seconds=10)
    async def auto_leave(self):
        # メンバーがいないのに接続している際はvoice_abandonedイベントを呼び出す。
        for voice_client in self.bot.voice_clients:
            if all(member.bot for member in voice_client.channel.members):
                self.bot.dispatch("voice_abandoned", voice_client)

    def clean(self, manager: Manager, reason: Optional[Any] = None) -> None:
        "渡されたManagerの後始末をします。"
        self.bot.loop.create_task(manager.disconnect(reason)) \
            .add_done_callback(lambda _: self.now.pop(manager.guild.id))

    def cog_unload(self):
        self.auto_leave.cancel()
        for manager in list(self.now.values()):
            self.clean(manager, {
                "ja": "再起動または機能更新のため切断しました。",
                "en": "Disconnected for reboot or feature update."
            })

        # もしお片付けされていないファイルがあるのなら削除しておく。
        for file_name in listdir(OUTPUT_DIRECTORY):
            if file_name.endswith(".wav"):
                self.bot.loop.create_task(remove(f"{OUTPUT_DIRECTORY}/{file_name}"))


def setup(bot):
    bot.add_cog(TTSCog(bot))