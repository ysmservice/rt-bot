# RT - Server Tool

from discord.ext import commands
import discord

from datetime import datetime, timedelta
from asyncio import TimeoutError
from random import sample


PERMISSION_TEXTS = {
    "administrator": "管理者",
    "view_audit_log": "監査ログを表示",
    "manage_guild": "サーバー管理",
    "manage_roles": "ロールの管理",
    "manage_channels": "チャンネルの管理",
    "kick_members": "メンバーをキック",
    "ban_members": "メンバーをBAN",
    "create_instant_invite": "招待を作成",
    "change_nickname": "ニックネームの変更",
    "manage_nicknames": "ニックネームの管理",
    "manage_emojis": "絵文字の管理",
    "manage_webhooks": "ウェブフックの管理",
    "view_guild_insights": "テキストチャンネルの閲覧＆ボイスチャンネルの表示",
    "send_messages": "メッセージを送信",
    "send_tts_messages": "TTSメッセージを送信",
    "manage_messages": "メッセージの管理",
    "embed_links": "埋め込みリンク",
    "attach_files": "ファイルを添付",
    "read_message_history": "メッセージ履歴を読む",
    "mention_everyone": "@everyone、@here、全てのロールにメンション",
    "external_emojis": "外部の絵文字の使用",
    "add_reactions": "リアクションの追加",
    "connect": "接続",
    "speak": "発言",
    "stream": "動画",
    "mute_members": "メンバーをミュート",
    "deafen_members": "メンバーのスピーカーをミュート",
    "move_members": "メンバーを移動",
    "use_voice_activation": "音声検出を使用",
    "priority_speaker": "優先スピーカー"
}


class ServerTool(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.trash_queue = []

    @commands.command(
        aliases=["perm"], extras={
            "headding": {
                "ja": "指定したユーザーの権限を表示します。",
                "en": "Displays the permissions of the specified user."
            }, "parent": "ServerTool"
        }
    )
    async def permission(self, ctx, member: discord.Member = None):
        """!lang ja
        -------
        指定されたユーザーの持っている権限を表示します。

        Parameters
        ----------
        member : メンバーのメンションか名前
            対象のメンバーのメンションまたは名前です。

        Aliases
        -------
        perm, 権限, けんげん

        !lang en
        --------
        Displays the permissions of the specified user.

        Parameters
        ----------
        member : Member mention or name
            Target member mention or name.

        Aliases
        -------
        perm"""
        if member is None:
            member = ctx.author

        await ctx.reply(
            embed=discord.Embed(
                title={
                    "ja": "権限一覧", "en": "Permissions"
                },
                description="`" + ("`, `".join(
                    PERMISSION_TEXTS[name]
                    for name in PERMISSION_TEXTS
                    if getattr(
                        member.guild_permissions, name, False
                    )) + "`"
                ), color=self.bot.colors["normal"]
            )
        )

    @commands.command(
        aliases=["serverinfo", "si"], extras={
            "headding": {
                "ja": "サーバーの情報を表示します。",
                "en": "Show server info."
            }, "parent": "ServerUseful"
        }
    )
    async def sinfo(self, ctx, guild_id: int = None):
        """!lang ja
        --------
        サーバーの情報を表示します。

        Parameters
        ----------
        guild_id : int, optional
            対象のサーバーのIDです。  
            指定しなかった場合はコマンドを実行したサーバーとなります。  
            RTのいるサーバーしかサーバー指定はできません。

        Aliases
        -------
        si

        !lang en
        --------
        Show you server info.

        Parameters
        ----------
        guild_id : int, optional
            The ID of the target server.  
            If it is not specified, it is the server where the command was executed.  
            Only the server where RT is located can be specified as the server.

        Aliases
        -------
        si"""
        if guild_id is None:
            guild = ctx.guild
        else:
            guild = self.bot.get_guild(guild_id)
            if guild is None:
                return await ctx.reply(
                    {"ja": "サーバーが見つかりませんでした。",
                     "en": "The server is not found."}
                )

        e = discord.Embed(title=f"{guild.name}の情報",
                          description="", color=0x00ff00)
        e.add_field(name="サーバー名(ID)", value=f"{guild.name}({guild.id})")
        chs = (len(guild.channels), len(guild.categories),
               len(guild.text_channels), len(guild.voice_channels))
        e.add_field(name="チャンネル数",
                    value="%s個(カテゴリ：%s個,テキスト：%s個,ボイス：%s個)" % chs)
        mbs = (len(guild.members),
               len([m for m in guild.members if not m.bot]),
               len([m for m in guild.members if m.bot]))
        e.add_field(name="メンバー数",
                    value="%s人(ユーザー：%s人,Bot：%s人)" % mbs)
        e.add_field(name="作成日時(UTC)", value=guild.created_at)
        e.set_thumbnail(url=guild.icon.url)

        await ctx.reply(embed=e)

    @commands.command(
        aliases=["timem", "tm", "たいむましん", "タイムマシン",
                 "バックトゥザフューチャー", "BackToTheFuture"],
        extras={
            "headding": {
                "ja": "過去のメッセージを表示します。",
                "en": "Displays past messages."
            }, "parent": "Individual"
        }
    )
    async def timemachine(self, ctx, day: int = 1):
        """!lang ja
        --------
        タイムマシンです。  
        指定した日数前のメッセージの内容とメッセージリンクを表示します。

        Parameters
        ----------
        day : int, default 1
            さかのぼる日数です。

        !lang en
        --------
        Time machine.  
        Displays the contents of messages and message links from the specified number of days ago.

        Parameters
        ----------
        day : int, default 1
            It is how many days ago the message should be."""
        await ctx.trigger_typing()

        async for message in ctx.channel.history(
                limit=1, before=datetime.now() - timedelta(days=day)
            ):
            e = discord.Embed(
                description=f"{message.content}\n[メッセージに行く]({message.jump_url})",
                color=self.bot.colors["normal"]
            )
            e.set_author(
                name=message.author.display_name,
                icon_url=message.author.avatar.url
            )
            e.set_footer(text=f"{day}日前のメッセージ | タイムマシン機能")
            await ctx.reply(embed=e)
            break
        else:
            await ctx.reply(
                {"ja": "過去にさかのぼりすぎました。",
                 "en": "I was transported back in time to another dimension."}
            )

    def easy_embed(
            self, content: str,
            color: discord.Color = discord.Embed.Empty
        ):
        es = ">>"
        spl = content.splitlines()
        title = spl[0][len(es):]
        desc, fields = [], {}

        footer = spl[-1][2:] if ';;' in spl[-1] else None
        if footer:
            spl.pop(-1)

        spl.pop(0)
        f = None
        for c in spl:
            if c == "":
                continue
            if c[0] == '<':
                f = c[1:] if '!' != c[1] else c[2:]
                fields[f] = {'i': True if '!' != c[1] else False, 'c': []}
                continue
            if f:
                fields[f]['c'].append(c)
                continue
            desc.append(c)

        e = discord.Embed(
            title=title,
            description='\n'.join(desc),
            color=color
        )
        for f in fields.keys():
            e.add_field(
                name=f,
                value='\n'.join(fields[f]['c']),
                inline=fields[f]['i']
            )
        if footer:
            e.set_footer(text=footer)

        return e

    @commands.command(
        aliases=["埋め込み"], extras={
            "headding": {
                "ja": "埋め込みメッセージを作成します。",
                "en": "Make embed message."
            }, "parent": "ServerUseful"
        }
    )
    async def embed(self, ctx, *, content):
        """!lang ja
        -------
        Embedを作成します。  
        以下のようにします。
        ```
        rt!embed タイトル
        説明
        ```
        そしてフィールドで分けたい場合は`<`または`<!`でできます。  
        ```
        rt!embed タイトル
        説明
        <フィールド名
        フィールド説明
        <フィールド名
        フィールド説明
        <!横にならばないフィールド名
        横に並ばないフィールド説明
        <!横に並ばないフィールド名
        横に並ばないフィールド名
        ```

        !lang en
        --------
        Make embed message.

        Examples
        --------
        ```
        rt!embed title
        description
        ```

        ```
        rt!embed Rule
        This is the rule.
        <!No1
        Do not talking.
        <!No2
        This is the false rule.
        ```"""
        await ctx.channel.webhook_send(
            username=ctx.author.display_name, avatar_url=ctx.author.avatar.url,
            embed=self.easy_embed(">>" + content)
        )

    @commands.command(
        aliases=["抽選", "choice", "lot"], extras={
            "headding": {
                "ja": "抽選をします。", "en": ""
            }, "parent": "ServerTool"
        }
    )
    async def lottery(self, ctx, count: int, role: discord.Role = None):
        """!lang ja
        --------
        指定された人数抽選をします。

        Parameters
        ----------
        count : int
            当たり数です。
        role : 役職のメンションか役職, optional
            抽選で選ばれる人で持っている必要のある役職です。  
            選択しなくても大丈夫です。

        !lang en
        --------
        Draws lots for the specified number of people.

        Parameters
        ----------
        count : int
            The number of hits.
        role : mention or position of the position, optional
            This is the role that must be held by the person who will be selected by lottery.  
            You don't need to select it."""
        target = ctx.guild.members
        if role:
            target = [member for member in target
                      if member.get_role(role.id)]
        embed = discord.Embed(
            title="抽選",
            description=", ".join(
                member.mention
                for member in sample(target, count)
            ),
            color=self.bot.colors["normal"]
        )
        await ctx.reply(embed=embed)

    @commands.command(
        extras={
            "headding": {
                "ja": "招待ランキング",
                "en": "Invite checker."
            }, "parent": "ServerUseful"
        }
    )
    async def invites(self, ctx):
        """!lang ja
        --------
        招待ランキングを表示します。

        !lang en
        --------
        Show you invite ranking."""
        await ctx.reply(
            embed=discord.Embed(
                title=f"{ctx.guild.name}の招待(招待数)ランキング",
                description='\n'.join(
                    a + '：`' + c + "`"
                        for a, c in sorted(
                            [(i.inviter.mention + '(' + i.code + ')',
                              str(i.uses))
                             for i in await ctx.guild.invites()],
                            reverse=True,
                            key=lambda p: int(p[1])
                        )
                    ),
                color=self.bot.colors["normal"]
            )
        )

    @commands.command(
        aliases=["delmes", "削除", "rm", "さくじょ"], extras={
            "headding": {
                "ja": "メッセージ削除コマンド、リアクションメッセージ削除",
                "en": "Delete message command, Delete message by reaction."
            }, "parent": "ServerTool"
        }
    )
    @commands.has_permissions(manage_messages=True)
    @commands.cooldown(1, 5)
    async def purge(self, ctx, count: int, target: discord.Member = None):
        """!lang ja
        --------
        メッセージ一括コマンドです。  
        リアクションによるメッセージ削除の説明は一番下にあります。

        Parameters
        ----------
        count : int
            削除するメッセージの数です。
        target : メンバーのメンションまたは名前, optional
            削除するメッセージの送信者を指定します。  
            選択しない場合は送信者関係なくメッセージを削除します。

        Examples
        --------
        `rt!purge 10`

        Aliases
        -------
        delmes, rm, 削除, さくじょ

        Notes
        -----
        リアクションによる範囲指定でのメッセージ削除も可能です。  
        やり方は🗑️のリアクションを削除したい複数のメッセージの一番下にまず付けます。  
        そして削除したいメッセージの一番上に同じように🗑️のリアクションをつけます。  
        これだけでできます。[使用例動画](https://youtu.be/cGnnUbVceR8)

        !lang en
        --------
        This is a message batch command.  
        The explanation of message deletion by reaction is at the bottom.

        Parameters
        ----------
        count : int
            The number of messages to delete.
        target : member's mention or name, optional
            Specify the sender of the message to be deleted.  
            If not selected, the message will be deleted regardless of the sender.

        Examples
        --------
        `rt!purge 10`.

        Aliases
        -------
        delmes, rm

        Notes
        -----
        It is possible to delete a message by specifying a range of reactions.  
        To do this, first put a 🗑️ reaction at the bottom of the messages you want to delete.  
        Then put the same 🗑️ reaction at the top of the message you want to delete.  
        This is the only way to do it. [Example Video](https://youtu.be/cGnnUbVceR8)"""
        await ctx.trigger_typing()
        await ctx.message.delete()
        await ctx.channel.purge(
            limit=count,
            check=lambda mes: target is None or mes.author.id == target.id,
            bulk=True
        )
        await ctx.reply("Ok", delete_after=3)

    EMOJIS = {
        "star": ("⭐", "🌟"),
        "trash": "🗑️"
    }

    @commands.Cog.listener()
    async def on_full_reaction_add(self, payload):
        if not payload.guild_id or not payload.member or payload.member.bot:
            return

        if (emoji := str(payload.emoji)) in self.EMOJIS["star"]:
            # スターボード
            for reaction in payload.message.reactions:
                if str(reaction.emoji) in self.EMOJIS["star"]:
                    async for user in reaction.users():
                        # もしRTがスターをつけてるなら既にスターボードに乗っているのでやめる。
                        if user.id == self.bot.user.id:
                            return
            else:
                channel = discord.utils.find(
                    lambda ch: ch.topic and "rt>star" in ch.topic,
                    payload.message.guild.text_channels
                )
                if channel:
                    await channel.send(
                        embed=discord.Embed(
                            title="スターがついたメッセージ",
                            description=(
                                f"{payload.message.content}\n[メッセージに行く]"
                                f"({payload.message.jump_url})"
                            ),
                            color=0xf2f2b0
                        ).set_author(
                            name=payload.message.author.display_name,
                            icon_url=payload.message.author.avatar.url
                        )
                    )
                    # スターボードにすでにあることを次スターがついた際にわかるようにスターを付けておく。
                    await payload.message.add_reaction(self.EMOJIS["star"][0])

        if (emoji == self.EMOJIS["trash"] and payload.channel_id not in self.trash_queue
                and payload.member.guild_permissions.manage_messages):
            # リアクションメッセージ削除
            self.trash_queue.append(payload.channel_id)
            try:
                new_payload = await self.bot.wait_for(
                    "full_reaction_add", timeout=45.0,
                    check=lambda new_payload: (
                        new_payload.member.id == payload.member.id
                        and new_payload.guild_id == payload.guild_id
                        and str(new_payload.emoji) == emoji
                    )
                )
            except TimeoutError:
                return
            else:
                await payload.message.channel.purge(
                    before=payload.message, after=new_payload.message, bulk=True
                )
                await payload.message.delete()
                await new_payload.message.delete()
            finally:
                self.trash_queue.remove(payload.channel_id)


def setup(bot):
    bot.add_cog(ServerTool(bot))