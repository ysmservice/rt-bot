# RT - TTS

from typing import Optional, Type, Dict, List

from aiofiles.os import remove as async_remove
from aiofiles import open as async_open
from os import listdir, remove
from os.path import exists

from urllib.parse import unquote
from functools import wraps

from discord.ext import commands, tasks
import discord

from jishaku.functools import executor_function
from base64 import encodebytes
from pydub import AudioSegment

from rtlib.page import EmbedPage
from rtlib.ext import componesy
from rtlib import websocket, RT

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
        "wav": ["mei", "man", "reimu", "marisa",
                "miku", "nero", "homu", "kaoru", "wacky"]
    }
    EMOJIS = {
        "error": "<:error:878914351338246165>"
    }

    def __init__(self, bot: RT):
        self.bot = bot
        self.cache: Dict[int, dict] = {}
        self.now: Dict[int, dict] = {}
        super(commands.Cog, self).__init__(bot.session, VOICES)
        self.bot.loop.create_task(self.on_ready())

    async def on_ready(self):
        super(VoiceManager, self).__init__(
            self.bot.data["mysql"]
        )
        await self.init_table()

        self.auto_leave.start()

    @commands.group(
        extras={
            "headding": {"ja": "ボイスチャンネルで読み上げをします。",
                         "en": "..."},
            "parent": "Entertainment"
        },
        aliases=["yomi", "yomiage", "読み上げ", "よみあげ"],
        slash_command=True,
        description="TTS"
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

    @tts.command(
        aliases=["connect", "じょいん", "接続"],
        description="読み上げを開始します。 / Start tts."
    )
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
        reply = ctx.reply
        if ctx.guild.voice_client:
            data = {
                "ja": "既に別のチャンネルに接続しています。",
                "en": "..."
            }
        elif not ctx.author.voice:
            data = {
                "ja": "ボイスチャンネルに接続してください。",
                "en": "..."
            }
        elif ctx.guild.id in self.bot.cogs["MusicNormal"].now:
            data = {
                "ja": "音楽プレイヤーと同時に使用することはできません。\nサブのRTであるりつたんを使用してください。",
                "en": "..."
            }
        else:
            if hasattr(ctx, "interaction"):
                reply = ctx.interaction.edit_original_message
                await ctx.reply("Now loading...")
            else:
                await ctx.trigger_typing()
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

        await reply(content=data)

    @tts.command(
        aliases=["disconnect", "dis", "切断", "せつだん"],
        description="読み上げを終了します。 / Stop tts."
    )
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
        if ctx.guild.voice_client:
            await ctx.guild.voice_client.disconnect()
        del self.now[ctx.guild.id]
        await ctx.reply(
            {"ja": "切断しました。",
             "en": "..."}
        )

    async def after_playing(
        self, guild: discord.Guild, file_path: str, e: Optional[Type[Exception]]
    ) -> None:
        # 読み上げ後は読み上げたファイルを削除してもう一度playを実行します。
        if (not file_path.startswith("http") and file_path != "None"
                and "routine" not in file_path):
            # 声がVOICEROIDの場合はダウンロードリンクを直接使い読み上げる。
            # それ以外の声の場合は音声ファイルを作成するので削除する必要がある。
            try:
                await async_remove(file_path)
            except FileNotFoundError:
                pass

        if guild.id in self.now:
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

            # もしネタ機能の音声ならそっちを再生する。
            for path in self.cache[message.author.id]["routine"]:
                for alias in self.cache[message.author.id]["routine"][path]["aliases"]:
                    if text == alias:
                        if self.bot.user.id == 888635684552863774:
                            url = f"http{'://localhost' if self.bot.test else 's://rt-bot.com'}/" \
                                f"api/tts/routine/get/{path[path.rfind('/') + 1:]}"
                        else:
                            url = path
                        break
                else:
                    continue
                break
            else:
                # もしネタ機能の音声じゃないなら普通に再生する準備をする。
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
                try:
                    url = await self.synthe(
                        voice, text, file_path,
                        rtchan=self.bot.user.id == 888635684552863774
                    ) or file_path
                except Exception as e:
                    print("TTS Error: ", e)
                    self.final_error = e
                    await self.after_playing(guild, "None", None)
                    try:
                        await message.add_reaction(self.EMOJIS["error"])
                    except:
                        pass
                    url = "None"

            # 再生終了後に実行する関数を用意する。
            after = lambda e: self.bot.loop.create_task(
                self.after_playing(guild, url, e))

            if url != "None":
                # もし文字列が存在するなら再生する。
                if "routine" in url:
                    kwargs = {"options": '-filter:a "volume=1.5"'}
                else:
                    vol = 2.2 if voice in ("reimu", "marisa") else 5.5
                    kwargs = {"options": f'-filter:a "volume={vol}"'}
                    if ext == "ogg":
                        kwargs["options"] += \
                            f" -ss {voiceroid.VOICEROIDS[voice]['zisa'] - 0.8}"

                # 音声を再生する。
                source = discord.PCMVolumeTransformer(
                    discord.FFmpegPCMAudio(url, **kwargs),
                    volume=self.now.get("volume", 1.0)
                )
                if source and guild.voice_client:
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
                and message.guild.voice_client
                and discord.utils.get(
                    message.guild.voice_client.channel.members,
                    id=message.author.id
                ) and message.content
                and message.channel.id in self.now[message.guild.id]["channels"]
                and not message.content.startswith(tuple(self.bot.command_prefix))
                and not message.content.startswith(("!", "?", ".", "#", "sb#", "sb."))):
            # 読み上げをします。
            self.now[message.guild.id]["queue"].append(message)
            if not self.now[message.guild.id]["playing"]:
                await self.play(message.guild)

    @tts.group(
        aliases=["ch", "ちゃんねる"],
        description="読み上げ対象チャンネルの追加、削除コマンド。"
    )
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

    @channel.command(
        name="add", aliases=["あどど", "ad"],
        description="読み上げ対象のチャンネルを追加します。 / Add tts target channel."
    )
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
        if len(self.now[ctx.guild.id]["channels"]) == 5:
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

    @channel.command(
        name="remove", aliases=["rm", "りむーぶ", "さくじょ"],
        description="読み上げ対象のチャンネルを削除します。 / Remove tts target channel."
    )
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

    @tts.group(
        name="dictionary", aliases=["dic", "じしょ", "辞書"],
        description="辞書の追加、削除コマンドです。 / Dictionary manage command."
    )
    async def guild_dictionary(self, ctx):
        """!lang ja
        --------
        読み上げ時に置き換える文字列を設定する辞書機能です。  
        `rt!tts dictionary`と実行すれば設定されている辞書一覧を見れます。

        Aliases
        -------
        dic, じしょ, 辞書

        !lang en
        --------
        ..."""
        if not ctx.invoked_subcommand:
            data = await self.read_dictionary(ctx.guild.id)
            embeds = []
            add_embed = lambda description, count: embeds.append(
                discord.Embed(
                    title={
                        "ja": f"辞書 {count}",
                        "en": f"Dictionary {count}"
                    },
                    description=description[:-1],
                    color=self.bot.colors["normal"]
                )
            )
            description = ""
            i, count = 0, 0
            for key in data:
                i += 1
                description += f"{key}：{data[key]}\n"
                if i == 10:
                    count += 1
                    add_embed(description, count)
                    i = 0
            if i != 10:
                count += 1
                add_embed(description, count)
            if count == 1:
                await ctx.reply(embed=embeds[0], view=EmbedPage(data=embeds))
            else:
                await ctx.reply(embeds=embeds)
            del embeds

    @guild_dictionary.command(
        name="show", description="読み上げの辞書を表示します。")
    async def show_dictionary(self, ctx):
        ctx.invoked_subcommand = False
        await self.guild_dictionary(ctx)

    @guild_dictionary.command(
        name="set", aliases=["せっと"],
        description="読み上げの辞書の追加をします。"
    )
    @commands.has_permissions(administrator=True)
    async def set_dictionary(
        self, ctx, before: str = discord.SlashOption(
            "target", "交換対象とする文字列です。"
        ), *, after: str = discord.SlashOption(
            "replace", "交換する文字列です。"
        )
    ):
        """!lang ja
        --------
        辞書を設定します。  
        30個まで設定可能です。

        Parameters
        ----------
        before : str
            置き換える対象の文字列です。
        after : str
            置き換える文字列です。

        Examples
        --------
        `rt!tts dictionary set yaakiyu 彼の名はやあきゆ、希少価値だ。`

        Aliases
        -------
        せっと

        !lang en
        --------
        ..."""
        data = await self.read_dictionary(ctx.guild.id)
        if len(data) == 30:
            await ctx.reply(
                {"ja": "辞書は30個より多く設定することはできません。",
                 "en": "..."}
            )
        else:
            data[before] = after
            await self.write_dictionary(data, ctx.guild.id)
            if ctx.guild.id in self.now:
                self.now[ctx.guild.id]["dictionary"] = data
            await ctx.reply("Ok")

    @guild_dictionary.command(
        name="delete", aliases=["でる", "rm", "remove", "del"],
        description="読み上げの辞書を削除します。"
    )
    @commands.has_permissions(administrator=True)
    async def delete_dictionary(
        self, ctx, *, word: str = discord.SlashOption(
            "target", "削除する辞書の交換対象名です。"
        )
    ):
        """!lang ja
        --------
        辞書を削除します。

        Parameters
        ----------
        word : str
            置き換える対象の文字列です。

        Aliases
        -------
        でる, rm, remove, del

        !lang en
        --------
        ..."""
        data = await self.read_dictionary(ctx.guild.id)
        if word in data:
            del data[word]
            if ctx.guild.id in self.now:
                self.now[ctx.guild.id]["dictionary"] = data
            await self.write_dictionary(data, ctx.guild.id)
            await ctx.reply("Ok")
        else:
            await ctx.reply(
                {"ja": "その辞書が見つかりませんでした。",
                 "en": "..."}
            )

    @tts.group(
        aliases=["ねた", "ネタ"],
        description="読み上げにネタ音声を追加、削除します。 / Add or remove routine voice."
    )
    async def routine(self, ctx):
        """!lang ja
        -------
        自分の好きなの音声を読み上げ時に使うようにできます。  
        例：`そうだよ(便乗)`, `FOO↑気持ちぃ〜`, `いいゾ〜これ`, `ないです`  
        **りつたんから登録することはできないのでRTから追加してください。**

        Aliases
        -------
        ねた, ネタ

        !lang en
        --------
        ..."""
        if not ctx.invoked_subcommand:
            data = await self.read_routine(ctx.author.id)
            embed = discord.Embed(
                title="Routine List",
                color=self.bot.colors["normal"]
            )
            for key in data:
                embed.add_field(
                    name=data[key]["file_name"],
                    value=", ".join(data[key]["aliases"])
                )
            await ctx.reply(embed=embed, replace_language=False)

    @routine.command(
        name="show", description="読み上げに追加されているネタ音声を表示します。 / Show routine voices."
    )
    async def show_routine(self, ctx):
        await self.routine(ctx)

    @routine.command()
    async def reload(self, ctx):
        """!lang ja
        --------
        ネタボイス(routine)の再読み込みをします。  
        このコマンドはRTのサブであるりつたんを使っている場合のみ使うコマンドです。  
        普通のRTでの実行は意味がありません。  
        このコマンドは実行者のRoutineの登録リストを再読み込みするコマンドです。  
        もしRTにネタボイスを追加した際にりつたんを使用していた場合は、このコマンドを実行しないとりつたんでネタボイスを使用できません。"""
        data = await self.read_routine(ctx.author.id)
        if ctx.author.id in self.cache:
            self.cache[ctx.author.id]["routine"] = data
        await ctx.reply("Ok")

    @executor_function
    def get_durations(self, path: str) -> float:
        return AudioSegment.from_file(path, path[path.rfind(".") + 1:]).duration_seconds

    @routine.command(
        name="add", aliases=["あどど"],
        description="ネタ音声を追加します。 / Add rutine voice."
    )
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def add_routine(
        self, ctx, *, aliases: str = discord.SlashOption(
            "triggers", "ネタ音声の再生のトリガーとなる文字列です。空白で複数選択可能です。 / Aliases."
        )
    ):
        """!lang ja
        --------
        ネタボイスを登録します。  
        対象の音声を添付してください。  

        Notes
        -----
        添付できる音声は3MBまでで7秒以内の必要があります。  
        そして登録できるネタボイスは20個までです。  
        対応しているフォーマットは`wav`と`ogg`です。

        Warnings
        --------
        RTのサブであるりつたんの場合はこのコマンドは実行できません。  
        RTからこのコマンドを実行してください。  
        もしりつたんの読み上げを使用中にRTからこのコマンドでネタボイスを追加した際は、りつたんの方で`rt#tts routine reload`を実行してください。  
        なお現在スラッシュコマンドによるネタボイスの追加はできないのですみませんが`rt!tts routine add`のようにして実行してください。

        Parameters
        ----------
        aliases : str
            空白か改行でわけた送信したら音声が流れる文字列です。  
            例：`そうだよ そうだよ(便乗) sdy mur`  
            (この中のどれかを送れば音声が流れる。)

        Examples
        --------
        `rt!tts routine add yeah Yeah そうだな おっ、そうだな`

        Aliases
        -------
        あどど

        !lang en
        --------
        ..."""
        if ctx.message.attachments and self.bot.user.id != 888635684552863774:
            data = await self.read_routine(ctx.author.id)
            if len(data) == 20:
                await ctx.reply(
                    {"ja": "既に20個登録されているためこれ以上登録できません。",
                     "en": "..."}
                )
            elif ctx.message.attachments[0].size > 3_145_728:
                await ctx.reply(
                    {"ja": "アップロードできる音声は約3MBまでです。",
                     "en": "..."}
                )
            elif ctx.message.attachments[0].url.endswith((".wav", ".ogg")):
                await ctx.trigger_typing()
                # セーブする。
                path = f"cogs/tts/routine/{ctx.author.id}-{ctx.message.attachments[0].filename}"
                await ctx.message.attachments[0].save(path)
                # 時間が7秒以上じゃないか確認する。
                if await self.get_durations(path) <= 7:
                    data[path] = {
                        "aliases": aliases.split(),
                        "file_name": ctx.message.attachments[0].filename
                    }
                    await self.write_routine(ctx.author.id, data)

                    if ctx.author.id in self.cache:
                        self.cache[ctx.author.id]["routine"] = data
                    await ctx.reply("Ok")
                else:
                    await ctx.reply(
                        {"ja": "音声は七秒以内で終わる必要があります。",
                         "en": "..."}
                    )
            else:
                await ctx.reply(
                    {"ja": "ファイルのフォーマットは`wav`, `ogg`のどれかの必要があります。",
                     "en": "..."}
                )
        else:
            await ctx.reply(
                {"ja": "登録する音声を追加してください。\nまたはりつたんに登録することはできません。",
                 "en": "..."}
            )

    @routine.command(
        name="remove", aliases=["rm", "りむーぶ", "del", "delete"],
        description="ネタ音声を削除します。 / Remove routine voice."
    )
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def remove_routine(
        self, ctx, *, alias: str = discord.SlashOption(
            "target", "削除するネタ音声に登録してる言葉です。"
        )
    ):
        """!lang ja
        --------
        登録したネタボイスを削除します。

        Parameters
        ----------
        alias : str
            削除する対象のネタボイスのトリガーとなる文字列の一つです。  
            例：`そうだよ(便乗)`

        Aliases
        -------
        rm, りむーぶ, del, delete"""
        data = await self.read_routine(ctx.author.id)
        if data and self.bot.user.id != 888635684552863774:
            await ctx.trigger_typing()

            files = []
            for key in list(data.keys()):
                if alias in data[key]["aliases"]:
                    del data[key]
                    await async_remove(key)
                    files.append(key)
            await self.write_routine(ctx.author.id, data)

            if ctx.author.id in self.cache:
                self.cache["routine"] = data

            async with self.bot.session.post(
                f"{self.bot.get_url()}/api/tts/routine/delete",
                json={"files": [path[path.rfind("/") + 1:] for path in files]}
            ) as r:
                self.bot.print("[TTS.RoutineDelete]", files)
                ...

            await ctx.reply("Ok")
        else:
            await ctx.reply(
                {"ja": "まだRoutineは追加されていません。\nまたはりつたんから削除することはできません。",
                 "en": "..."}
            )

    async def on_member(self, event_type: str, member: discord.Member) -> None:
        if member.guild.id in self.now:
            # メンバーがボイスチャンネルに接続または切断した際に呼び出される関数です。
            # そのメンバーが設定している声のキャッシュを取得または削除をします。
            if event_type == "join":
                self.cache[member.id] = {
                    "voice": await self.read_voice(member.id),
                    "routine": await self.read_routine(member.id)
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
        if before.channel and after.channel and before.channel.id != after.channel.id:
            # もしメンバーがボイスチャンネルを移動したなら。
            self.bot.dispatch("voice_leave", member, before, after)
            self.bot.dispatch("voice_join", member, before, after)
        elif not before.channel:
            # もしメンバーがボイスチャンネルに接続したなら。
            self.bot.dispatch("voice_join", member, before, after)
            await self.on_member("join", member)
        elif not after.channel:
            # もしメンバーがボイスチャンネルから切断したなら。
            self.bot.dispatch("voice_leave", member, before, after)
            await self.on_member("leave", member)

    async def on_select_voice(self, select, interaction):
        # もしvoiceコマンドで声の種類を設定されたら呼び出される関数です。
        if select.values:
            if interaction.user.id in self.cache:
                self.cache[interaction.user.id]["voice"] = select.values[0]
            await self.write_voice(interaction.user.id, select.values[0])
            await interaction.message.channel.send(
                {"ja": f"{interaction.user.mention}, 設定しました。",
                 "en": f"{interaction.user.mention}, Ok"},
                target=interaction.user.id
            )
            await interaction.message.delete()

    @tts.command(
        aliases=["声", "こえ", "vcset", "vc"],
        description="読み上げの声を変更します。 / Change tts voice."
    )
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
        # 読み上げを終わらせておく。
        for guild_id in list(self.now.keys()):
            self.bot.loop.create_task(
                self.now[guild_id]["guild"].voice_client.disconnect()
            )
            del self.now[guild_id]

        self.now = {}

        # 削除されていないファイルがあるならそのファイルを削除する。
        for file_name in listdir("cogs/tts/outputs"):
            try:
                remove(f"cogs/tts/outputs/{file_name}")
            except Exception as e:
                print("Passed error on TTS:", e)

        self.bot.loop.create_task(self.tts_routine.close())

        self.auto_leave.cancel()

    async def do_nothing(self, _):
        pass

    @commands.Cog.listener()
    async def on_voice_abandoned(self, voice_client):
        # もしメンバーがいないのに接続されているチャンネルがあるなら自動で抜け出す。
        if voice_client.channel.guild.id in self.now:
            channel = self.bot.get_channel(
                self.now[voice_client.channel.guild.id]["channels"][0]
            )
            ctx = type(
                "Context", (), {
                    "reply": self.do_nothing,
                    "guild": voice_client.channel.guild,
                    "author": voice_client.channel.members[0]
                }
            )
            await self.leave(ctx)
            await channel.send(
                "誰もいないので読み上げを終了します。"
            )

    @tasks.loop(seconds=10)
    async def auto_leave(self):
        # メンバーがいないのに接続している際はそのイベントを呼び出す。
        for voice_client in self.bot.voice_clients:
            if all(member.bot for member in voice_client.channel.members):
                self.bot.dispatch("voice_abandoned", voice_client)

    @executor_function
    def aioexists(self, path: str) -> bool:
        return exists(path)

    @websocket.websocket("/api/tts/routine/loader", auto_connect=True, reconnect=True)
    async def tts_routine(self, ws: websocket.WebSocket, _):
        "りつたんからTTSのRoutineをバックエンドを経由して使うためのウェブソケット通信です。"
        await ws.send("ready")

    @tts_routine.event("load")
    async def test(self, ws: websocket.WebSocket, filename: str):
        # Routineのファイルを返す。
        if "%" in filename:
            filename = unquote(filename)
        # ファイルがあるか確認をする。
        path = f"cogs/tts/routine/{filename}"
        if await self.aioexists(path):
            async with async_open(path, "rb") as f:
                data = {
                    "filename": filename,
                    "data": encodebytes(await f.read()).decode()
                }
            async with self.bot.session.post(
                f"{self.bot.get_url()}/api/tts/routine/post", json=data
            ) as r:
                self.bot.print("[TTS.RoutineUploader]", filename, await r.json())
                ...
            await ws.send("ok")
        else:
            await ws.send("not_found")


def setup(bot):
    bot.add_cog(TTS(bot))
