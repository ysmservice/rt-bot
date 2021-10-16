# RT - AutoMod

from typing import TYPE_CHECKING, Optional, Union, Dict, List

from discord.ext import commands, tasks
import discord

from collections import defaultdict
from time import time

from .constants import CACHE_TIMEOUT, DEFAULT_LEVEL, DefaultWarn
from .modutils import check, assertion_error_handler
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
        この機能は`rt!automod setup`を実行すれば使えるようになります。  
        この機能で実行した処罰のログは`rt>modlog`がチャンネルトピックにあるチャンネルに送信されます。  
        このログチャンネルは作っておくことを推奨します。

        Notes
        -----
        スパム対策機能はデフォルトでは警告数が3になったらミュートで5でBANとなります。  
        そしてスパム検知レベルはデフォルトでは2で二回スパムしたと検知されると警告数が一つ上がります。  
        これらは設定で変更が可能です。  
        なお警告数はしばらくしたら30分以内にリセットされます。  
        それと管理者は処罰されません。  
        ミュートはデフォルトではオフですので設定をしましょう。

        Warnings
        --------
        NekoBotなどの画像を表示するだけのような娯楽コマンドを何回か送信して、スパムとして検知されるということが起きかねません。  
        そのためそのようなBotがある場合はそれらのようなBotのためのチャンネルを作り例外設定にそのチャンネルを追加しましょう。  
        これのやり方の詳細についてはこれからででてくる`rt!automod ignore`コマンドのヘルプを見てください。  
        **説明をしっかり読まないと痛いめ見ます。**  
        特に先ほど言った通りミュートはデフォルトでオフです。BANの警告数をミュートのデフォルトに設定するかミュートを設定するかしましょう。  
        そして先ほど言った通り`rt!automod setup`をしないと機能しません。

        Aliases
        -------
        am, 安全, モデレーション

        !lang en
        --------
        Automatic moderation with anti-spam, emoji restrictions, and invite-only channel restrictions.  
        This is the number of warnings that will be added when someone spams.  
        You can create a behavior such as banning or muting when the number reaches this number.  
        This feature is available only when `rt! automod setup`.

        Notes
        -----
        By default, the anti-spam function mutes the user when the number of warnings reaches 3, and bans the user when the number reaches 5.  
        The spam detection level is 2 by default, and if you are detected as spamming twice, the warning number goes up by one.  
        These can be changed in the settings.

        Warnings
        --------
        You can send a couple of entertainment commands, such as a NekoBot, that just display images, and get spammed.
        So if you have such Bots, create channels for them and add them to the exception list.
        More details on how to do this will come later in `rt! automod ignore` command.
        **If you don't read the explanation carefully, it will hurt.**

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
        デフォルトでは3となっています。  
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
        The default is 3.
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
        --------
        いくつの警告数になったらBANをするかを設定します。

        Parameters
        ----------
        warn : float
            いくつの警告数にするかです。

        Notes
        -----
        デフォルトは5です。

        Warnings
        --------
        低く設定した場合誤検出のスパムでBANされかねないので低く設定するのは非推奨です。

        Aliases
        -------
        バン, 禁止

        !lang en
        --------
        Set the number of warnings to BAN.

        Parameters
        ----------
        warn : float
            How many warnings?

        Notes
        -----
        The default is 5.

        Warnings
        --------
        Setting it low is not recommended, as it can result in BAN for false positive spam."""
        await self.update_setting(
            ctx, {
                "ja": f"BANをする警告数を`{warn}`にしました。",
                "en": f"The number of warnings to ban has been set to `{warn}`."
            }, "ban", warn
        )

    @automod.command(aliases=["l", "レベル"])
    @check
    @assertion_error_handler(
        {"ja": "レベルは1以上100以下である必要があります。",
         "en": "The level must be between 1 and 100, inclusive."}
    )
    async def level(self, ctx, level: int):
        """!lang ja
        --------
        スパム検知レベルを設定するコマンドです。  
        設定したレベルの数だけスパムとして認識したら警告数を一つ上げます。  
        デフォルトは2で二回スパムとして認識されたら警告数を一つあげるということになります。

        Parameters
        ----------
        level : int
            設定するスパム検知レベルです。

        Notes
        -----
        1以上100以下である必要があります。

        Warnings
        --------
        そレベルを100などの高い数にするとスパムが検知されても処罰がされるまでとっても時間がかかります。  
        なので普通は変えるとしても1~4までのどこかにするのを推奨します。

        !lang en
        --------
        This command sets the spam detection level.
        Raise the number of warnings by one if the number of levels you set is recognized as spam.
        The default is 2, which means that if it is seen twice as spam, it will raise one warning.

        Parameters
        ----------
        level: int
            The spam detection level to set.

        Notes
        -----
        Must be between 1 and 100, inclusive.

        Warnings
        --------
        A low number such as 1 will be a big problem.
        And if you set the level to a high number such as 100, it will take a very long time for spam to be detected and punished.
        So I usually recommend to change it to somewhere up to 2 ~ 6."""
        await self.update_setting(
            ctx, {
                "ja": f"スパム検知レベルを`{level}`に設定しました。",
                "en": f"Spam detection level set to `{level}`."
            }, "level", level
        )

    @automod.command(aliases=["e", "絵文字"])
    @check
    @assertion_error_handler(
        {"ja": "絵文字数規制の絵文字数は0以上4000以下である必要があります。",
         "en": "The number of pictograms in the pictogram count restriction must be between 0 and 4000."}
    )
    async def emoji(self, ctx, count: int):
        """!lang ja
        --------
        送信しても良い絵文字の数を設定します。  
        この送信可能絵文字数を超えた数の絵文字を送信した場合は警告数が`0.5`上がります。

        Parameters
        ----------
        count : int
            送信しても良い絵文字の数です。  
            0以上4000以下である必要があります。

        Notes
        -----
        これはデフォルトでオフです。  
        もしこれを設定する場合ルールの記載するなどした方が親切です。

        Aliases
        -------
        e, 絵文字

        !lang en
        --------
        You can set the number of pictographs that can be sent.
        If you send more emoji than this number, the number of warnings increases by `0.5`.

        Parameters
        ----------
        count : int
            The number of pictographs that can be sent.
            Must be greater than or equal to 0 and less than or equal to 4000.

        Notes
        -----
        This is off by default.
        If you set this up, it would be helpful to write down the rules.

        Aliases
        -------
        e"""
        await self.update_setting(
            ctx, {
                "ja": f"メッセージで有効な絵文字の数を`{count}`で設定しました。",
                "en": f"The number of valid emoji in a message is now set by `{count}`."
            }, "emoji", count
        )

    @automod.group(aliases=["例外", "無視", "igs"])
    async def ignore(self, ctx):
        """!lang ja
        --------
        スパムとしてチェックを行わない例外のチャンネルまたはロールを設定できます。

        Aliases
        -------
        igs, 例外, 無視

        !lang en
        --------
        You can configure channels or roles for exceptions that are not checked as spam.

        Aliases
        -------
        igs"""
        if not ctx.invoked_subcommand:
            await self.ignore_list(ctx)

    @ignore.command("add", aliases=["追加"])
    @check
    @assertion_error_handler(
        {"ja": "その例外は既に追加されています。",
         "en": "The exception is already added."}
    )
    async def add_ignore(self, ctx, *, obj: Union[discord.TextChannel, discord.Role]):
        """!lang ja
        -------
        スパムを検知しないチャンネルまたは持っていたらスパム検知をしないロールを設定します。。

        Parameters
        ----------
        channelOrRole : テキストチャンネルかロールのメンションまたはロール
            例外に設定するチャンネルかロールです。

        Notes
        -----
        Nekobotなどの画像表示などのコマンドを実行するチャンネルなどに設定すると良いです。

        Warnings
        --------
        例外チャンネルということはそのチャンネルではスパムをしても何も処罰はされないということです。  
        ですのでクールダウンを設定するなどをすることを推奨します。  
        Tips:RTの`cooldown`コマンドで`3`秒などにクールダウンを設定できます。

        Aliases
        -------
        追加

        !lang en
        --------
        Set a channel that will not detect spam or a role that will not detect spam if you have it.

        Parameters
        ----------
        channelOrRole : a mention or role of a text channel or role
            The channel or role to set as an exception.

        Notes
        -----
        It is good to set it to a channel to execute commands such as displaying images such as Nekobot.

        Warnings
        --------
        An exception channel means that spamming on that channel won't get you punished.
        So I recommend you to set cooldown.
        Tips: You can set the cooldown to `3` seconds using the RT `cooldown` command."""
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
        """!lang ja
        --------
        例外設定を削除します。

        Parameters
        ----------
        channelOrRole : テキストチャンネルかロールのメンションまたはロール
            例外に設定したチャンネルかロールです。

        Aliases
        -------
        rm, del, delete, 削除

        !lang en
        --------
        Remove the exception configuration.

        Parameters
        ----------
        channelOrRole : a mention or role of a text channel or role
            The channel or role to set as an exception.

        Aliases
        -------
        rm, del, delete"""
        await self.update_setting(
            ctx, {
                "ja": f"例外リストから{obj.mention}を削除しました。",
                "en": f"I removed {obj.mention} from exception list."
            }, "remove_ignore", obj.id
        )

    @ignore.command("list", aliases=["一覧", "l"])
    async def ignore_list(self, ctx):
        """!lang ja
        --------
        設定されている例外のリストです。

        Aliases
        -------
        l, 一覧

        !lang en
        --------
        Display the exception configuration.

        Aliases
        -------
        l"""
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
        """!lang ja
        --------
        招待を規制します。  
        この機能を有効にすると指定されたチャンネル以外で作成した招待リンクは自動で削除されます。  
        ※管理者権限を持っている人は作っても削除されません。

        Aliases
        -------
        ie, 招待

        !lang en
        --------
        Restrict invitations.  
        When this function is enabled, invitation links created outside the specified channel are automatically deleted.  
        *People with administrative rights are not deleted when they are created.

        Aliases
        -------
        ie"""
        if not ctx.invoked_subcommand:
            await self.invites_list(ctx)

    @invites.command()
    @check
    @assertion_error_handler(PLZ)
    async def onoff(self, ctx):
        """!lang ja
        --------
        招待リンク規制の有効または無効を切り替えします。

        !lang en
        --------
        Enable or disable invitation link restrictions."""
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
        """!lang ja
        --------
        招待リンクの作成が可能なチャンネルのリストを表示します。

        Aliases
        -------
        l, 一覧

        !lang en
        --------
        Displays a list of channels for which you can create invitation links.

        Aliases
        -------
        l"""
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
        """!lang ja
        --------
        招待リンク作成可能チャンネルリストにこのコマンドを実行したチャンネルを追加します。  
        `rt!automod invites onoff on`で招待リンク規制を有効にしていないと追加しても無効です。

        Aliases
        -------
        a, 追加

        !lang en
        --------
        Adds the channel on which you run this command to the Invite Links Available Channels list.  
        `rt!automod invites onoff on`, and you do not enable the invite link restriction.

        Aliases
        -------
        a"""
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
        """!lang ja
        --------
        招待リンク作成可能チャンネルリストからこのコマンドを実行したチャンネルを削除します。

        Aliases
        -------
        rm, del, delete, 削除

        !lang en
        --------
        Removes the channel on which you run this command from the Invite Link Creatable Channels list.

        Aliases
        -------
        rm, del, delete"""
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
        """!lang ja
        --------
        即抜け後にすぐ参加した人をBANする設定です。  
        サーバー参加後に指定した秒数以内に退出そして参加をした場合にそのユーザーをBANするという設定です。

        Parameters
        ----------
        seconds : int
            何秒以内に退出して参加をしたらBANをするかです。

        Aliases
        -------
        wd, 即抜けBAN

        !lang en
        --------
        This is the setting to BAN the person who joined immediately after the instant exit.
        BAN the user if the user exits and joins within the specified number of seconds after joining the server.

        Parameters
        ----------
        seconds: int
            Within how many seconds you have to leave to participate in BAN.

        Aliases
        -------
        wd"""
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

    @tasks.loop(minutes=15)
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