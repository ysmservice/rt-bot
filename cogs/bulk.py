# RT - Bulk

from discord.ext import commands
import discord

from typing import Tuple, List


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

    @commands.group()
    async def bulk(self, ctx):
        """!lang ja
        --------
        一括でメンバー全員に役職を付与したりメッセージの送信をしたりできます。
        
        !lang en
        --------
        ..."""
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
        ..."""
        await ctx.trigger_typing()

        failed_members: List[Tuple[discord.Member, str]] = []
        for member in ctx.guild.members:
            if member.id != ctx.author.id:
                # もし送信対象が役職でmemberが役職を持っていないならcontinueする。
                if isinstance(target, discord.Role):
                    if member.get_role(target.id) is None:
                        continue

                try:
                    await member.send(content)
                except (discord.HTTPException, discord.Forbidden):
                    failed_members.append((member, "権限不足またはメンバーがDMを許可していませえん。"))
                except Exception as e:
                    failed_members.append((member, f"何らかの理由で遅れませんでした。`{e}`"))

        embed = discord.Embed(
            title={"ja": "メッセージ一括送信が完了しました。", "en": "..."},
            color=self.bot.colors["normal"]
        )
        embed.add_field(
            name={"ja": "送信失敗したメンバー一覧", "en": "..."},
            value=("\n".join(f"{member.mention}\n　{e}"
                             for member, e in failed_members)
                   if failed_members
                   else {
                       "ja": "送信に失敗したメンバーはいません。",
                       "en": "..."
                    })
        )
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
        ..."""
        await ctx.trigger_typing()
        if mode == "add":
            for member in ctx.guild.members:
                # もし対象者が特定の役職を持っている人でその役職をmemberが持ってないならcontinueする。
                if isinstance(target, discord.Role):
                    if member.get_role(target.id) is None:
                        continue
                try:
                    await member.add_roles(role)