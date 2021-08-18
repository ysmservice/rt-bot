# RT - TTS

from discord.ext import commands, tasks
import discord

from typing import Dict, List, Type
from rtlib.ext import componesy
from aiofiles.os import remove
from functools import wraps
from os import listdir
from time import time

from .voice_manager import VoiceManager, voiceroid
from .data_manager import DataManager
from data import voices as VOICES


def require_connected(coro):
    # 接続していないと実行できないコマンドに付けるデコレータです。
    @wraps(coro)
    async def new_coro(self, ctx, *args, **kwargs):
        if not ctx.author.voice:
            await ctx.reply(
                {"ja": "ボイスチャンネルに接続していません。",
                 "en": "..."}
            )
        elif ctx.guild.id in self.now:
            return await coro(self, ctx, *args, **kwargs)
        else:
            await ctx.reply(
                {"ja": "ボイスチャンネルに接続していません。\n`rt!tts join`を実行しましょう。",
                 "en": "..."}
            )
    return new_coro


class TTS(commands.Cog, VoiceManager, DataManager):

    VOICE_FORMAT: Dict[str, List[str]] = {
        "wav": ["mei", "man", "reimu", "marisa"]
    }

    def __init__(self, bot):
        self.bot = bot
        self.cache: Dict[int, dict] = {}
        self.now: Dict[int, dict] = {}
        super(commands.Cog, self).__init__(bot.session, VOICES)

    @commands.Cog.listener()
    async def on_ready(self):
        self.db = await self.bot.data["mysql"].get_database()
        super(VoiceManager, self).__init__(self.db)
        await self.init_table()

    @commands.group(
        extras={
            "headding": {"ja": "ボイスチャンネルで読み上げをします。",
                         "en": "..."},
            "parent": "Entertainment"
        },
        aliases=["yomi", "yomiage", "読み上げ", "よみあげ"]
    )
    async def tts(self, ctx):
        """!lang ja
        --------
        ボイスチャンネルで読み上げをします。

        Aliases
        -------
        yomi, yomiage, 読み上げ

        !lang en
        --------
        ..."""
        if not ctx.invoked_subcommand:
            await ctx.reply(
                {"ja": "使用方法が違います。",
                 "en": "..."}
            )

    @tts.command(aliases=["connect", "じょいん", "接続"])
    async def join(self, ctx):
        """!lang ja
        --------
        ボイスチャンネルに接続させこのコマンドを実行したチャンネルにでたメッセージを読み上げます。

        Aliases
        -------
        connect, 接続, じょいん

        !lang en
        --------
        ..."""
        if ctx.guild.voice_client:
            data = {
                "ja": "既に別のチャンネルに接続しています。",
                "en": "..."
            }
        elif not ctx.author.voice:
            data = {
                "ja": "ボイスチャンネにに接続してください。",
                "en": "..."
            }
        else:
            data = {
                "ja": "接続しました。",
                "en": "..."
            }

            self.now[ctx.guild.id] = {
                "guild": ctx.guild,
                "dictionary": await self.read_dictionary(ctx.guild.id),
                "queue": [],
                "playing": False,
                "channels": [ctx.channel.id]
            }
            await ctx.author.voice.channel.connect()
            for member in ctx.author.voice.channel.members:
                await self.on_member("join", member)

        await ctx.reply(data)

    @tts.command(aliases=["disconnect", "dis", "切断", "せつだん"])
    @require_connected
    async def leave(self, ctx):
        """!lang ja
        --------
        読み上げを切断させます。

        Aliases
        -------
        disconnect, dis, 切断, せつだん

        !lang en
        --------
        ..."""
        await ctx.guild.voice_client.disconnect()
        del self.now[ctx.guild.id]
        await ctx.reply(
            {"ja": "切断しました。",
             "en": "..."}
        )

    async def after_playing(
            self, guild: discord.Guild, file_path: str, e: Type[Exception]
        ) -> None:
        # 読み上げ後は読み上げたファイルを削除してもう一度playを実行します。
        if not file_path.startswith("http") and file_path != "None":
            # 声がVOICEROIDの場合はダウンロードリンクを直接使い読み上げる。
            # それ以外の声の場合は音声ファイルを作成するので削除する必要がある。
            await remove(file_path)
        self.now[guild.id]["playing"] = False
        # もう一度再生をする。
        await self.play(guild)

    async def play(self, guild: discord.Guild) -> None:
        # キューにメッセージがあるなら再生を行います。
        if self.now[guild.id]["queue"]:
            self.now[guild.id]["playing"] = True
            # 色々必要なデータなどを取り出す。
            message = self.now[guild.id]["queue"].pop(0)
            text = message.clean_content
            data = self.now[guild.id]

            # カスタム辞書にあるものを交換する。
            for word in data["dictionary"]:
                text = text.replace(word, data["dictionary"][word])

            # ファイル名を用意する。
            voice = self.cache[message.author.id]["voice"]
            if voice in self.VOICE_FORMAT["wav"]:
                ext = "wav"
            else:
                ext = "ogg"
            file_path = f"cogs/tts/outputs/{message.channel.id}_{message.id}.{ext}"

            # 音声合成をする。
            url = await self.synthe(voice, text, file_path) or file_path
            # 再生終了後に実行する関数を用意する。
            after = lambda e: self.bot.loop.create_task(
                self.after_playing(guild, url, e))

            if url != "None":
                # もし文字列が存在するなら再生する。
                vol = 4.5 if voice in ("reimu", "marisa") else 7.5
                kwargs = {"options": f'-filter:a "volume={vol}"'}
                if ext == "ogg":
                    kwargs["options"] += f" -ss {voiceroid.VOICEROIDS[voice]['zisa'] - 0.8}"

                # 音声を再生する。
                source = discord.PCMVolumeTransformer(
                    discord.FFmpegPCMAudio(url, **kwargs),
                    volume=self.now.get("volume", 1.0)
                )
                if source:
                    guild.voice_client.play(source, after=after)
                else:
                    after(None)
            else:
                after(None)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if not message.guild:
            return

        if (message.guild.id in self.now and message.author.id in self.cache
                and discord.utils.get(
                    message.guild.voice_client.channel.members,
                    id=message.author.id
                ) and message.content
                and message.channel.id in self.now[message.guild.id]["channels"]):
            # 読み上げをします。
            self.now[message.guild.id]["queue"].append(message)
            if not self.now[message.guild.id]["playing"]:
                await self.play(message.guild)

    @tts.group(aliases=["ch", "ちゃんねる"])
    @require_connected
    async def channel(self, ctx):
        """!lang ja
        --------
        読み上げ対象のチャンネルを管理します。  
        `rt!tts channel`と実行すると現在読み上げ対象となっているチャンネル一覧が表示されます。

        Aliases
        -------
        ch, ちゃんねる

        !lang en
        --------
        ..."""
        if not ctx.invoked_subcommand:
            await ctx.reply(
                "* " + "\n* ".join(
                    f"<#{ch}>" for ch in self.now[ctx.guild.id]["channels"]
                ), replace_language=False
            )

    @channel.command(name="add", aliases=["あどど", "ad"])
    @require_connected
    async def add_channel(self, ctx):
        """!lang ja
        --------
        読み上げ対象のチャンネルを追加します。  
        5個まで登録できます。

        Aliases
        -------
        あどど, ad

        !lang en
        --------
        ..."""
        if len(self.now[cts.guild.id]["channels"]) == 5:
            await ctx.reply(
                {"ja": "五個まで追加可能です。",
                 "en": "..."}
            )
        else:
            self.now[ctx.guild.id]["channels"].append(ctx.channel.id)
            await ctx.reply(
                {"ja": "読み上げ対象チャンネルを追加しました。",
                 "en": "..."}
            )

    @channel.command(name="remove", aliases=["rm", "りむーぶ", "さくじょ"])
    @require_connected
    async def remove_channel(self, ctx):
        """!lang ja
        --------
        読み上げ対象のチャンネルを削除します。

        Aliases
        -------
        rm, りむーぶ, さくじょ

        !lang en
        --------
        ..."""
        if len(self.now[ctx.guild.id]["channels"]) == 1:
            await ctx.reply(
                {"ja": "読み上げ対象のチャンネルがなくなってしまいます。",
                 "en": "..."}
            )
        else:
            if ctx.channel.id in self.now[ctx.guild]:
                self.now[ctx.guild.id]["channels"].remove(ctx.channel.id)
                await ctx.reply(
                    {"ja": "読み上げ対象チャンネルを削除しました。",
                     "en": "..."}
                )
            else:
                await ctx.reply(
                    {"ja": "このチャンネルは読み上げ対象ではありません。",
                     "en": "..."}
                )

    async def on_member(self, event_type: str, member: discord.Member) -> None:
        # メンバーがボイスチャンネルに接続または切断した際に呼び出される関数です。
        # そのメンバーが設定している声のキャッシュを取得または削除をします。
        if event_type == "join":
            self.cache[member.id] = {
                "voice": await self.read_voice(member.id)
            }
        elif member.id in self.voices:
            del self.cache[member.id]

    @commands.Cog.listener()
    async def on_voice_state_update(
            self, member: discord.Member,
            before: discord.VoiceState,
            after: discord.VoiceState
        ) -> None:
        # on_member_join/leaveのどっちかを呼び出すためのものです。

        if member.guild.id in self.now:
            if not before.channel:
                # もしメンバーがボイスチャンネルに接続したなら。
                await self.on_member("join", member)
            elif not after.channel:
                # もしメンバーがボイスチャンネルから切断したなら。
                await self.on_member("leave", member)

    async def on_select_voice(self, select, interaction):
        # もしvoiceコマンドで声の種類を設定されたら呼び出される関数です。
        if select.values:
            if interaction.user.id in self.cache:
                self.cache[interaction.user.id]["voice"] = select.values[0]
            await self.write_voice(interaction.user.id, select.values[0])
            await interaction.message.channel.send(
                {"ja": f"{interaction.user.mention}, 設定しました。",
                 "en": f"{interaction.user.mention}, ..."},
                target=interaction.user.id
            )
            await interaction.message.delete()

    @tts.command(aliases=["声", "こえ", "vcset", "vc"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def voice(self, ctx):
        """!lang ja
        --------
        読み上げ時に使用する声を変更します。  
        実行すると選択ボックスが現れます。

        Aliases
        -------
        声, こえ, vc, vcset

        !lang en
        --------
        ..."""
        view = componesy.View("TtsVoiceSelect")
        view.add_item(
            "Select", self.on_select_voice,
            options=[
                discord.SelectOption(
                    label=VOICES[voice]["name"], value=voice,
                    description=VOICES[voice]["description"]
                ) for voice in VOICES
            ], placeholder="声の種類を選択 / Select Voice"
        )
        await ctx.reply("下のメニューバーから声を選択してください。", view=view)

    def cog_unload(self):
        self.now = {}
        self.delete_files.cancel()

    @tasks.loop(minutes=1)
    async def delete_files(self):
        # 削除されていないファイルがあるならそのファイルを削除する。
        for file_name in listdir("cogs/tts/outputs"):
            try:
                await remove(file_name)
            except Exception as e:
                print("Passed error on TTS:", e)


def setup(bot):
    bot.add_cog(TTS(bot))
