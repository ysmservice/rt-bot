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

    @commands.group(
        aliases=["安全", "モデレーション", "am"], extras={
            "headding": {
                "ja": "スパム対策などのモデレーション機能",
                "en": "moderation features such as anti-spam"
            }, "parent": "ServerSafety"
        }
    )
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @commands.guild_only()
    async def automod(self, ctx):
        """!lang ja
        --------
        スパム対策機能や絵文字制限そして招待可能チャンネル規制などの機能がある自動モデレーション機能です。  
        これから警告数というワードがでますがこれは誰かがスパムをした際などに加算される警告の数です。  
        この数がいくつになったらBANやミュートをするといった動作を作ることができます。

        Notes
        -----
        スパム対策機能はデフォルトでは警告数が4になったらミュートで7でBANとなります。  
        そしてスパム検知レベルはデフォルトでは2で二回スパムしたと検知されると警告数が一つ上がります。  
        これらは設定で変更が可能です。

        Aliases
        -------
        am, 安全, モデレーション

        !lane en
        --------
        Automatic moderation with anti-spam, emoji restrictions, and invite-only channel restrictions.  
        This is the number of warnings that will be added when someone spams.  
        You can create a behavior such as banning or muting when the number reaches this number.

        Notes
        -----
        By default, the anti-spam function mutes the user when the number of warnings reaches 4, and bans the user when the number reaches 7.  
        The spam detection level is 2 by default, and if you are detected as spamming twice, the warning number goes up by one.  
        These can be changed in the settings.

        Aliases
        -------
        am"""
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
        """!lang ja
        --------
        モデレーション機能を有効化します。  
        これを実行するとスパム対策機能が作動します。  
        (招待リンク規制や絵文字規制は設定をしないとデフォルトでは有効になりません。)

        Aliases
        -------
        設定

        !lang en
        --------
        Activate the moderation function.  
        Doing so will activate the anti-spam feature.  
        (Invitation link restrictions and emoji restrictions will not be enabled by default unless you set them up.)  """
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
        """!lang ja
        --------
        モデレーションを機能を無効にします。

        Aliases
        -------
        終了

        !lang en
        --------
        Disables the moderation feature."""
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
        """!lang ja
        --------
        警告数を管理するためのコマンドです。

        Aliases
        -------
        w, 警告

        !lang en
        --------
        This command is used to manage the number of warnings.

        Aliases
        -------
        w"""
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
        """!lang ja
        --------
        指定したメンバーの警告数を設定します。  
        設定した場合はその人の警告数がチェックされるため、BANまたはミュートする警告数に設定した警告数が達している場合は処罰が実行されます。  
        警告数は0以上100以下である必要があります。

        Parameters
        ----------
        warn : float
            設定する警告数です。  
            小数点を含むじょのにできます。
        target : メンバーのメンションまたは名前
            警告数を設定する対象のメンバーです。

        Aliases
        -------
        s, 設定

        !lang en
        --------
        Set the number of warnings for the specified member.  
        If set, the number of warnings for that person will be checked, and if the number of warnings set reaches the number of warnings to be banned or muted, the punishment will be executed.  
        The number of warnings must be between 0 and 100.

        Parameters
        ----------
        warn : float
            The number of warnings to set.  
            The number of warnings to set, including decimal points.
        target : member mention or name
            The target member for which to set the number of warnings.

        Aliases
        -------
        s"""
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
        """!lang ja
        --------
        いくつの警告数になったら何のロールを付与してミュートにするかを設定します。

        Parameters
        ----------
        warn : float
            いくつの警告数になったらミュートにするかです。
        role : ロールのメンションまたは名前
            ミュートする際に付与するロールです。

        Warnings
        --------
        警告数を低く設定しすぎるとたまたまスパムとして誤検出されただけでミュートなどになりかねません。  
        これには注意してください。  
        そしてこれはデフォルトでは無効となっています。  
        理由は仕組みはロール付与によるミュートだからです。  
        なので設定をしないとスパムする人がいてもミュートはしません。  
        (ですがご安心を、その人がスパムし続ける場合はBANされます。)

        Notes
        -----
        デフォルトでは4となっています。  
        また、ロールを付与ではなく剥奪もしたいという場合は`linker`という機能を使ってみましょう。  
        `rt!help linker`からヘルプを表示できます。

        Aliases
        -------
        m, ミュート

        !lang en
        --------
        Set the number of warnings to be granted and muted.

        Parameters
        ----------
        warn : float
            How many warnings are there before you mute them?
        role : The name or mention of the role
            The role to grant when muting.

        Warnings
        --------
        If you set the number of warnings too low, you may end up muting the spam just by chance.
        Be careful with this.
        This is disabled by default.
        The reason is that the mechanism is mute by roll.
        So if you don't set it up, it won't mute people who spam you.
        (But don't worry, if they keep spamming, they'll be BAN.)

        Notes
        -----
        The default is 4.
        If you also want to revoke a role rather than grant it, you can use `linker`.
        `rt!help linker`."""
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
        """!lang ja
        --------"""
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

    @tasks.loop(minutes=30)
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