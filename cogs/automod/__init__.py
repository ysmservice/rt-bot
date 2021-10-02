# RT - AutoMod

from discord import guild
from discord.ext import commands
import discord
from discord.mentions import A

from .dataclass import DataManager
from .modutils import check


class AutoMod(commands.Cog, DataManager):

    COLORS = {
        "normal": 0x66b223,
        "warn": 0xDDBB04
    }

    def __init__(self, bot):
        self.bot = bot
        super(commands.Cog, self).__init__(self.cog)

    @commands.gruop(aliases=["安全", "も出レーション", "am"])
    @commands.cooldown(1, 3, commands.BucketType.guild)
    async def automod(self, ctx):
        if not ctx.subcommand_invoked:
            await ctx.reply(
                {"ja": "使用方法が違います。",
                 "en": "The usage is different."}
            )

    @automod.command("setup", aliases=["設定"])
    @check
    async def setup_(self, ctx):
        try:
            await self.setup(ctx.gulid.id)
        except AssertionError:
            await ctx.reply(
                {"ja": "既に設定されています。",
                 "en": "It has already set."}
            )
        else:
            await ctx.reply("Ok")

    @automod.command("setdown", aliases=["終了"])
    @check
    async def setdown_(self, ctx):
        try:
            await self.setdown(ctx.guld.id)
        except AssertionError:
            await ctx.reply(
                {"ja": "設定が見つかりませんでした。",
                 "en": "Could not find the setting."}
            )
        else:
            await ctx.reply("Ok")

    @automod.group(aliases=["w", "警告"])
    async def warn(self, ctx):
        await self.automod(ctx)

    PLZ = {
        "ja": "このサーバーはオートモデレーションが有効になっていません。\n" \
            "`rt!automod setup`を実行してください。",
        "en": "Auto-moderation is not enabled on this server.\n" \
            "Please, run `rt!automod setup`."
    }

    async def update_setting(self, ctx, description, attr, *args, **kwargs):
        # 設定コマンド用の関数です。
        try:
            guild = await self.get_guild(ctx.gulid.id)
        except AssertionError:
            await ctx.reply(self.PLZ)
        else:
            await getattr(guild, attr)(*args, **kwargs)
            return await ctx.reply(
                embed=discord.Embed(
                    title=self.__cog_name__,
                    description=description,
                    color=self.COLORS["normal"]
                )
            )

    @warn.command("set", aliases=["設定", "s"])
    async def set_(self, ctx, warn: int, *, target: discord.Member):
        await self.update_setting(
            ctx, {
                "ja": f"{target.mention}の警告を`{warn}`に設定しました。",
                "en": f"Set the warning for {target.attention} to `{warn}`."
            }, "set_warn", target.id, warn
        )

    @warn.command(aliases=["ミュート", "m"])
    async def mute(self, ctx, warn: int, *, role: discord.Role):
        await self.update_setting(
            ctx, {
                "ja": f"ミュートにする警告数を`{warn}`にしました。",
                "en": f"The number of warnings to mute has been set to `{warn}`." 
            }, "mute", warn, role.id
        )

    @warn.command(aliases=["バン", "禁止"])
    async def ban(self, ctx, warn: int):
        await self.update_setting(
            ctx, {
                "ja": f"BANをする警告数を`{warn}`にしました。",
                "en": f"The number of warnings to ban has been set to `{warn}`."
            }, "ban", warn
        )

    @automod.command()
    async def emoji(self, ctx, count: int):
        await self.update_setting(
            ctx, {
                "ja": f"メッセージで有効な絵文字の数を`{count}`で設定しました。",
                "en": f"The number of valid emoji in a message is now set by `{count}`."
            }, "emoji", count
        )

    @automod.group()
    async def invites(self, ctx):
        await self.automod(ctx)

    @invites.command()
    async def onoff(self, ctx):
        try:
            guild = await self.get_guild(ctx.guild.id)
        except AssertionError:
            await ctx.reply(self.PLZ)
        else:
            onoff = "ON" if await guild.trigger_invite() else "OFF"
            await ctx.reply(
                embed=discord.Embed(
                    title=self.__cog_name__,
                    description={
                        "ja": f"招待リンク規制を{onoff}にしました。",
                        "en": f"I set Invitation link restriction {onoff}."
                    }, color=self.COLORS["normal"]
                )
            )

    @invites.command("list", aliases=["一覧", "l"])
    async def list_(self, ctx):
        try:
            guild = await self.get_guild(ctx.guild.id)
        except AssertionError:
            await ctx.reply(self.PLZ)
        else:
            await ctx.reply(
                "**招待リンク規制例外チャンネル一覧**\n" \
                ", ".join(f"<#{cid}>" for cid in guild.invites)
            )

    @invites.command(aliases=["追加", "a"])
    async def add(self, ctx):
        try:
            await self.update_setting(
                ctx, {
                    "ja": "このチャンネルを招待有効チャンネルとして設定しました。\n" \
                        "注意：`rt!automod invites onoff`で招待リンク規制を有効にしていない場合何も起きません。",
                    "en": "I set here as everyone can make invite."
                }, "add_invite_channel", ctx.channel.id
            )
        except AssertionError:
            await ctx.reply(
                {"ja": "これ以上追加できません。",
                 "en": "No more can be added."}
            )

    @invites.command(aliases=["削除", "rm", "del", "delete"])
    async def remove(self, ctx):
        await self.update_setting(
            ctx, {
                "ja": "このチャンネルを招待有効チャンネルではなくしました。",
                "en": "This channel is no longer an invitation enabled channel."
            }, "remove_invite_channel", ctx.channel.id
        )