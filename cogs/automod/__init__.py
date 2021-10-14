# RT - AutoMod

from typing import TYPE_CHECKING, Optional, Union, Dict, List

from discord.ext import commands, tasks
import discord

from collections import defaultdict
from time import time

from .modutils import check, assertion_error_handler
from .constants import CACHE_TIMEOUT
from .dataclass import DataManager

if TYPE_CHECKING:
    from .types import SpamCacheData as CacheData
    from .dataclass import Guild
    from rtlib import Backend


class AutoMod(commands.Cog, DataManager):

    COLORS = {
        "normal": 0x66b223,
        "warn": 0xDDBB04,
        "error": 0xF288AA
    }

    def __init__(self, bot):
        self.bot: "Backend" = bot
        self.cache: Dict[int, Dict[int, "CacheData"]] = defaultdict(
            lambda : defaultdict(dict))
        self.guild_cache: List[int] = []
        self.withdrawal_cache: Dict[int, int] = {}

        self.remove_cache.start()
        self.reset_warn.start()

        for name in ("message", "invite_create", "member_join"):
            self.bot.add_listener(self.trial, f"on_{name}")

        super(commands.Cog, self).__init__(self)

    @commands.group(aliases=["安全", "モデレーション", "am"])
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @commands.guild_only()
    async def automod(self, ctx):
        """!lang ja
        --------
        スパム対策機能や"""
        if not ctx.invoked_subcommand:
            await ctx.reply(
                {"ja": "使用方法が違います。",
                 "en": "The usage is different."}
            )

    @automod.command("setup", aliases=["設定"])
    @check
    @assertion_error_handler(
        {"ja": "既に設定されています。",
         "en": "It has already set."}
    )
    async def setup_(self, ctx):
        await self.setup(ctx.guild.id)
        if ctx.guild.id not in self.guild_cache:
            self.guild_cache.append(ctx.guild.id)
        await ctx.reply(
            embed=self.make_embed(
                {"ja": "AutoModを有効にしました。\n",
                 "en": "I enabled AutoMod."}
            )
        )

    @automod.command("setdown", aliases=["終了"])
    @check
    @assertion_error_handler(
        {"ja": "設定が見つかりませんでした。",
         "en": "Could not find the setting."}
    )
    async def setdown_(self, ctx):
        await self.setdown(ctx.guild.id)
        if ctx.guild.id in self.guild_cache:
            self.guild_cache.remove(ctx.guild.id)
        await ctx.reply(
            embed=self.make_embed(
                {"ja": "AutoModを無効にしました。",
                 "en": "I disabled AutoMod."}
            )
        )

    @automod.group(aliases=["w", "警告"])
    async def warn(self, ctx):
        """"""
        if not ctx.invoked_subcommand:
            await self.automod(ctx)

    def make_embed(self, description: Union[str, Dict[str, str]], **kwargs) -> discord.Embed:
        # AutoModの返信用の埋め込みを作る関数です。
        if "color" not in kwargs:
            kwargs["color"] = self.COLORS["normal"]
        return discord.Embed(
            title=self.__cog_name__,
            description=description, **kwargs
        )

    PLZ = {
        "ja": "このサーバーはオートモデレーションが有効になっていません。\n" \
            "`rt!automod setup`を実行してください。",
        "en": "Auto-moderation is not enabled on this server.\n" \
            "Please, run `rt!automod setup`."
    }

    async def update_setting(self, ctx, description, attr, *args, **kwargs):
        # 設定コマンド用の関数です。
        try:
            guild = await self.get_guild(ctx.guild.id)
        except AssertionError:
            await ctx.reply(self.PLZ)
        else:
            await getattr(guild, attr)(*args, **kwargs)
            await ctx.reply(embed=self.make_embed(description))
            return guild

    WARN_ERROR = {
        "ja": "警告数は0以上100以下である必要があります。",
        "en": "The number of warnings to ban must be between 0 and 100."
    }

    @warn.command("set", aliases=["設定", "s"])
    @check
    @assertion_error_handler(WARN_ERROR)
    async def set_(self, ctx, warn: float, *, target: discord.Member):
        if warn >= 0:
            guild = await self.update_setting(
                ctx, {
                    "ja": f"{target.mention}の警告を`{warn}`に設定しました。",
                    "en": f"Set the warning for {target.mention} to `{warn}`."
                }, "set_warn", target.id, warn
            )
            await guild.trial_user(target)
        else:
            await ctx.reply("警告数はゼロ以上である必要があります。")

    @warn.command(aliases=["ミュート", "m"])
    @check
    @assertion_error_handler(WARN_ERROR)
    async def mute(self, ctx, warn: float, *, role: discord.Role):
        await self.update_setting(
            ctx, {
                "ja": f"ミュートにする警告数を`{warn}`にしました。",
                "en": f"The number of warnings to mute has been set to `{warn}`." 
            }, "mute", warn, role.id
        )

    @warn.command(aliases=["バン", "禁止"])
    @check
    @assertion_error_handler(WARN_ERROR)
    async def ban(self, ctx, warn: float):
        await self.update_setting(
            ctx, {
                "ja": f"BANをする警告数を`{warn}`にしました。",
                "en": f"The number of warnings to ban has been set to `{warn}`."
            }, "ban", warn
        )

    @automod.command()
    @check
    @assertion_error_handler(
        {"ja": "絵文字数規制の絵文字数は0以上4000以下である必要があります。",
         "en": "The number of pictograms in the pictogram count restriction must be between 0 and 4000."}
    )
    async def emoji(self, ctx, count: int):
        await self.update_setting(
            ctx, {
                "ja": f"メッセージで有効な絵文字の数を`{count}`で設定しました。",
                "en": f"The number of valid emoji in a message is now set by `{count}`."
            }, "emoji", count
        )

    @automod.group(aliases=["例外", "無視", "igs"])
    async def ignore(self, ctx):
        if not ctx.invoked_subcommand:
            await self.ignore_list(ctx)

    @ignore.command("add", aliases=["追加"])
    @check
    @assertion_error_handler(
        {"ja": "その例外は既に追加されています。",
         "en": "The exception is already added."}
    )
    async def add_ignore(self, ctx, *, obj: Union[discord.TextChannel, discord.Role]):
        await self.update_setting(
            ctx, {
                "ja": f"例外リストに`{obj.name}`を追加しました。",
                "en": f"I added `{obj.name}` to ignore list."
            }, "add_ignore", obj.id
        )

    @ignore.command("remove", aliases=["削除", "rm", "del", "delete"])
    @check
    @assertion_error_handler(
        {"ja": "その例外が見つかりませんでした。",
         "en": "The exception is not found."}
    )
    async def remove_ignore(self, ctx, *, obj: Union[discord.TextChannel, discord.Role]):
        await self.update_setting(
            ctx, {
                "ja": f"例外リストから{obj.mention}を削除しました。",
                "en": f"I removed {obj.mention} from exception list."
            }, "remove_ignore", obj.id
        )

    @ignore.command("list", aliases=["一覧", "l"])
    async def ignore_list(self, ctx):
        data = (await self.get_guild(ctx.guild.id)).data
        if "ignores" in data:
            await ctx.reply(
                embed=self.make_embed(
                    ", ".join(
                        getattr(
                            ctx.guild.get_channel(sid) or ctx.guild.get_role(sid),
                            "mention", "*見つかりませんでした。*"
                        ) for sid in data["ignores"]
                    )
                )
            )
        else:
            await ctx.reply(
                {"ja": "例外リストは空です。",
                 "en": "Exception list is nothing."}
            )

    @automod.group(aliases=["ie", "招待"])
    async def invites(self, ctx):
        if not ctx.invoked_subcommand:
            await self.invites_list(ctx)

    @invites.command()
    @check
    @assertion_error_handler(PLZ)
    async def onoff(self, ctx):
        onoff = "ON" if await (
            await self.get_guild(ctx.guild.id)
        ).trigger_invite() else "OFF"
        await ctx.reply(
            embed=self.make_embed(
                {
                    "ja": f"招待リンク規制を{onoff}にしました。",
                    "en": f"I set Invitation link restriction {onoff}."
                }
            )
        )

    @invites.command("list", aliases=["一覧", "l"])
    @assertion_error_handler(PLZ)
    async def invites_list(self, ctx):
        await ctx.reply(
            "**招待リンク規制例外チャンネル一覧**\n" \
            ", ".join(
                f"<#{cid}>" for cid in (
                    await self.get_guild(ctx.guild.id)
                ).invites
            )
        )

    @invites.command(aliases=["追加", "a"])
    @check
    @assertion_error_handler(
        {"ja": "これ以上追加できません。",
         "en": "No more can be added."}
    )
    async def add(self, ctx):
        await self.update_setting(
            ctx, {
                "ja": "このチャンネルを招待有効チャンネルとして設定しました。\n" \
                    "注意：`rt!automod invites onoff`で招待リンク規制を有効にしていない場合何も起きません。",
                "en": "I set here as everyone can make invite."
            }, "add_invite_channel", ctx.channel.id
        )

    @invites.command(aliases=["削除", "rm", "del", "delete"])
    @check
    async def remove(self, ctx):
        await self.update_setting(
            ctx, {
                "ja": "このチャンネルを招待有効チャンネルではなくしました。",
                "en": "This channel is no longer an invitation enabled channel."
            }, "remove_invite_channel", ctx.channel.id
        )

    @automod.command(aliases=["即抜けBAN", "wd"])
    @check
    @assertion_error_handler(
        {"ja": "秒数は10以上300以下である必要があります。",
         "en": "Seconds must be 10 to 300 inclusive."}
    )
    async def withdrawal(self, ctx, seconds: int):
        await self.update_setting(
            ctx, {
                "ja": f"即抜けBANを`{seconds}`秒で設定しました。",
                "en": f"We set it to BAN when a member joins the server and leaves within `{seconds}` seconds."
            }, "set_withdrawal", seconds
        )

    def cog_unload(self):
        self.remove_cache.cancel()
        self.reset_warn.cancel()

    @tasks.loop(seconds=30)
    async def remove_cache(self):
        # スパム検知に使う前回送信されたメッセージのキャッシュの削除を行うループです。
        now, removed = time(), []
        for cid in list(self.cache.keys()):
            for uid in list(self.cache[cid].keys()):
                if now - self.cache[cid][uid]["time"] >= CACHE_TIMEOUT:
                    del self.cache[cid][uid]
                    removed.append(cid)
            if not self.cache[cid]:
                del self.cache[cid]
        # 即抜けBANのキャッシュを削除する。
        for mid, next_ in list(self.withdrawal_cache.items()):
            if now >= next_:
                del self.withdrawal_cache[mid]

    async def _get_guild(
        self, guild_id: int, if_not_exists_remove: bool = True
    ) -> Optional["Guild"]:
        # Gulid(automod.)クラスのインスタンスを取得する関数です。
        # もしguild_cacheにあるのに見つからなかったら、guild_cacheからそのサーバーを除去します。
        try:
            guild = await self.get_guild(guild_id)
        except AssertionError:
            if if_not_exists_remove and guild_id in self.guild_cache:
                self.guild_cache.remove(guild_id)
        else:
            return guild

    @tasks.loop(hours=14)
    async def reset_warn(self):
        # 警告数をリセットするループです。
        for guild_id in self.guild_cache:
            if (guild := await self._get_guild(guild_id)):
                for user_id in list(guild.data.get("warn", {}).keys()):
                    if guild.data["warn"][user_id]:
                        await guild.set_warn(user_id, 0.0)

    async def trial(self, obj: Union[discord.Message, discord.Invite, discord.Member]):
        # 罰するかしないかをチェックするべきイベントで呼ばれる関数でモデレーションを実行します。
        if obj.guild and obj.guild.id in self.guild_cache:
            if (guild := await self._get_guild(obj.guild.id)):
                await getattr(guild, f"trial_{obj.__class__.__name__.lower()}")(obj)


def setup(bot):
    bot.add_cog(AutoMod(bot))