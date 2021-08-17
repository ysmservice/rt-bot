# RT - TTS

from discord.ext import commands
import discord

from rtlib.ext import componesy
from typing import Dict
from funtools import wraps

from .voice_manager import VoiceManager
from .data_manager import DataManager
from data import voices as VOICES


def require_connected(coro):
    # 接続していないと実行できないコマンドに付けるデコレータです。
    @wraps(coro)
    async def new_coro(self, ctx, *args, **kargs):
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
    def __init__(self, bot):
        self.bot = bot
        self.voices: Dict[int, str] = {}
        self.now = {}
        super(commands.Cog, self).__init__(bot.session, voices)

    @commands.Cog.listener()
    async def on_ready(self):
        self.db = await bot.data["mysql"].get_database()
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
        if not ctx.subcommand_invoked:
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
            self.now[ctx.guild.id] = {
                "guild": ctx.guild,
                "dictionary": await self.read_dictionary(ctx.guild.id),
                "queue": []
            }
            await ctx.author.voice.channel.connect()
            data = {
                "ja": "接続しました。",
                "en": "..."
            }
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
        await ctx.author.voice.channel.disconnect()
        del self.now[ctx.guild.id]
        await ctx.reply(
            {"ja": "切断しました。",
             "en": "..."}
        )

    @commands.Cog.listener()
    async def on_message(self, message) -> None:
        if (message.guild.id in self.now and message.author.id in self.voices
                and discord.utils.get(
                    message.guild.voice_client.channel.members,
                    id=message.author.id
                )):
            # 読み上げをします。
            pass

    async def on_member(self, event_type: str, member: discord.Member) -> None:
        # メンバーがボイスチャンネルに接続または切断した際に呼び出される関数です。
        # そのメンバーが設定している声のキャッシュを取得または削除をします。
        if event_type == "join":
            self.voices[member.id] = await self.read_voice(member.id)
        elif member.id in self.voices:
            del self.voices[member.id]

    @commands.Cog.listener()
    async def on_voice_state_update(
            self, member: discord.Member,
            before: discord.VoiceState,
            after: discord.VoiceState
        ) -> None:
        # on_member_join/leaveのどっちかを呼び出すためのものです。
        channel_id = getattr(member.guild.voice_client, "channel.id", 0)
        if (channel_id == member.voice.channel.id
                and member.guild.id in self.now):
            join = len(before.channel.members) < len(after.channel.members)
            members = (after.channel.members if join
                        else before.channel.members)
            for member in members:
                target = bool(
                    discord.utils.get(
                        (before.channel.members
                            if join else after.channel.members),
                        id=member.id
                    )
                )
                if join and target:
                    # もしメンバーがボイスチャンネルに接続したなら。
                    await self.on_member("join", member)
                elif not join and not target:
                    # もしメンバーがボイスチャンネルから切断したなら。
                    await self.on_member("leave", member)

    async def on_select_voice(self, select, interaction):
        # もしvoiceコマンドで声の種類を設定されたら呼び出される関数です。
        if select.values:
            if interaction.user.id in self.voices:
                self.voices[interaction.user.id] = select.values[0]
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
                discod.SelectOption(
                    label=VOICES[voice]["name"], value=voice,
                    description=VOICES[voice]["description"]
                ) for voice in VOICES
            ], placeholder="声の種類を選択 / Select Voice"
        )
        await ctx.reply(view=view)


def setup(bot):
    bot.add_cog(TTS(bot))