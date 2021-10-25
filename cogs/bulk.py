# RT - Bulk

from discord.ext import commands
import discord


class GuildRole(commands.Converter):
    async def convert(self, ctx, arg):
        if arg == "everyone":
            return "guild"
        else:
            if "<" in arg:
                return ctx.guild.get_role(int(arg[3:-1]))
            else:
                return discord.utils.get(ctx.guild.roles, name=arg)


class Bulk(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def add_error_field(self, embed: discord.Embed,
                        failed_members: list, t: str) -> discord.Embed:
        # ここのtには`送信`とかが入る。
        embed.add_field(
            name={"ja": f"{t}に失敗したメンバー一覧",
                  "en": f"List of members who failed {t}"},
            value=("\n".join(f"{member.mention}\n　{e}"
                             for member, e in failed_members)
                   if failed_members
                   else {
                       "ja": f"{t}に失敗したメンバーはいません。",
                       "en": f"No member has failed {t}."
                    })
        )
        return embed

    @commands.group(
        extras={
            "headding": {
                "ja": "一括で指定した役職またはサーバーメンバー全員にメッセージを送信や役職の付与/剥奪ができます。",
                "en": "Adds or removes the specified role or sends the specified message to specific members who is on this server."
            },
            "parent": "ServerTool"
        }
    )
    async def bulk(self, ctx):
        """!lang ja
        --------
        一括でメンバー全員に役職を付与したりメッセージの送信をしたりできます。
        
        !lang en
        --------
        It can send a message and add a role for some members.
        """
        if not ctx.invoked_subcommand:
            await ctx.reply("使用方法が違います。")

    @bulk.command()
    async def send(self, ctx, target: GuildRole, *, content):
        """!lang ja
        --------
        指定されたメッセージを実行したサーバーにいるメンバー全員に送信します。
        
        Parameters
        ----------
        target : everyoneまたは役職の名前かメンション
            送る相手です。  
            もしeveryoneならサーバーにいる人全員です。  
            役職の名前かメンションにすればその役職を持っている人のみにメッセージが送信されます。
        content : str
            送る内容です。

        Examples
        --------
        ```
        rt!bulk send @ゲーマー **来月開催する予定のゲーム大会について**
        このゲーム大会では以下のゲームのスコアを競います。
        * MinecraftのPvP
        * Apex
        * スターフォックス64
        * パノラマコットン
        ```
        
        !lang en
        --------
        Sends the specified message to specific members who is on this server.
        
        Parameters
        ----------
        target : everyone or the role's name(mention)
            The target to send the message.
            `everyone` sends to all the members in the server.
            A role's name(mention) sends to only members who has the role.
        
        Examples
        --------
        ```
        rt!bulk send @Gamer **About the tournament of the games in next month**
        You will compete with these score:
        * Minecraft(PvP)
        * Apex
        * Fortnite
        * Super smash bros Special
        ```
        """
        await ctx.trigger_typing()

        failed_members = []

        for member in ctx.guild.members:
            if member.id != ctx.author.id and not member.bot:
                # もし送信対象が役職でmemberが役職を持っていないならcontinueする。
                if isinstance(target, discord.Role):
                    if member.get_role(target.id) is None:
                        continue

                try:
                    await member.send(content)
                except (discord.HTTPException, discord.Forbidden) as e:
                    failed_members.append(
                        (member, "権限不足またはメンバーがDMを許可していません。"))
                except Exception as e:
                    failed_members.append(
                        (member, f"何らかの理由で送れませんでした。`{e}`"))

        embed = discord.Embed(
            title={"ja": "メッセージ一括送信が完了しました。", "en": "It has completed to send the message to the members collectively."},
            color=self.bot.colors["normal"]
        )
        embed = self.add_error_field(embed, failed_members, "送信")
        await ctx.reply(embed=embed)

    @bulk.command()
    @commands.has_permissions(manage_roles=True)
    async def role(self, ctx, mode, target: GuildRole, role: discord.Role):
        """!lang ja
        --------
        実行したサーバーにいるメンバー全員に指定された役職を付与または剥奪をします。
        
        Parameters
        ----------
        mode : add または remove
            付与か剥奪どっちを実行するかで、addにすると役職の付与でremoveにすると役職の剥奪となります。
        target : everyoneまたは役職の名前かメンション
            役職の付与または剥奪を行う対象者です。  
            everyoneにした場合はサーバーにいる人全員となります。  
            役職の名前かメンションを入れた場合はその役職を持っている人が対象となります。
        role : 役職名または役職メンション
            付与または剥奪する役職です。

        !lang en
        --------
        Adds or Removes the specified role to specific members who is on this server.
        
        Parameters
        ----------
        mode : add or remove
            Add or Remove the role literally.
        target : everyone or the role's name(mention)
            The target to send the message.
            `everyone` adds/removes to all the members in the server.
            A role's name(mention) adds/removes to only members who has the role.
        role : Role's name or mention
            A role witch adds or removes.
        """
        await ctx.trigger_typing()
        
        if mode not in ("add", "remove"):
            raise commands.errors.CommandError(
                "引数modeはaddまたはremoveが使えます。")

        failed_members = []

        for member in ctx.guild.members:
            if not member.bot:
                # もし対象者が特定の役職を持っている人でその役職をmemberが持ってないならcontinueする。
                if isinstance(target, discord.Role):
                    if member.get_role(target.id) is None:
                        continue
                try:
                    if mode == "add":
                        await member.add_roles(role)
                    else:
                        await member.remove_roles(role)
                except (discord.Forbidden, discord.HTTPException):
                    failed_members.append(
                        (member, "権限が足りないかなんかでできませんでした。")
                    )
                except Exception as e:
                    failed_members.append(
                        (member, f"なんらかの原因でできませんでした。`{e}`")
                    )

        embed = discord.Embed(
            title={"ja": "役職付与/剥奪の一括送信が完了しました。", "en": "It has completed to add/remove a role to the members collectively."},
            color=self.bot.colors["normal"]
        )
        embed = self.add_error_field(embed, failed_members, "役職の付与/剥奪")
        await ctx.reply(embed=embed)


def setup(bot):
    bot.add_cog(Bulk(bot))
