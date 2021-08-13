# RT - Ticket

from discord.ext import commands, tasks
import discord

from time import time


class Ticket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldown = {}

    @commands.command(
        extras={
            "headding": {
                "ja": "チケットチャンネル作成用のパネルを作成します。",
                "en": "..."
            },
            "parent": "ServerPanel"
        }
    )
    @commands.has_permissions(manage_channels=True)
    async def ticket(self, ctx, title, description, role: discord.Role = None):
        """!lang ja
        --------
        チケットチャンネル作成用のパネルを作成します。

        Parameters
        ----------
        title : str, default 
            チケットパネルのタイトルです。
        description : str
            チケットパネルの説明欄に入れる文章です。  
            改行や空白を含めたい場合は`"`で文章を囲んでください。
        role : 役職名または役職のメンション, optional
            作成されるチケットチャンネルを見ることのできる役職です。  
            指定しない場合は管理者権限を持っている人とチケットチャンネル作成者本人のみが見れます。

        Notes
        -----
        このコマンドはチャンネル管理権限がある人でしか実行できません。  
        作成されるチケットパネルは🎫のリアクションが付与され、このリアクションを押すことでチケットチャンネルが作成されます。  
        もしこのパネルを無効化したい場合は単純に作成したパネルを削除すれば良いです。

        Examples
        --------
        `rt!ticket 問い合わせ  モデレーター`"""
        if ctx.guild and ctx.channel.category and str(ctx.channel.type) == "text":
            embed = discord.Embed(
                title=title,
                description=description,
                color=self.bot.colors["normal"]
            )
            message = await ctx.webhook_send(
                username=ctx.author.name, avatar_url=ctx.author.avatar.url,
                content=f"RTチケットパネル, {getattr(role, 'id', '...')}",
                embed=embed, wait=True, replace_language=False
            )
            await message.add_reaction("🎫")
        else:
            await ctx.reply(
                {"ja": "このコマンドはカテゴリーにあるテキストチャンネルのみ動作します。",
                 "en": "..."}
            )

    def make_channel_name(self, name: str) -> str:
        # チケットチャンネル用の名前を作る関数です。
        return (name[:90] if len(name) > 90 else name) + "-rtチケット"

    async def on_full_reaction(self, payload):
        if (str(payload.emoji) != "🎫" or payload.member.bot
                or not payload.message.embeds or not payload.message.guild
                or not payload.message.content.startswith("RTチケットパネル, ")):
            return

        # リアクションを追加/削除した人の名前でチケットチャンネル名を作る。
        channel_name = self.make_channel_name(payload.member.display_name)
        # リアクションを押した人が既にチャンネルを作成している場合はそのチャンネルを取得する。
        channel = discord.utils.get(payload.message.guild.text_channels,
                                    name=channel_name)

        if payload.event_type == "REACTION_ADD":
            # もしリアクションが押されたなら。
            # クールダウンが必要ならチャンネルを作成しない。
            now = time()
            if (error := now - self.cooldown.get(payload.member.id, 0)) < 300:
                await payload.message.channel.send(
                    {"ja": f"{payload.member.mention}, クールダウンが必要なため{error}秒待ってください。",
                     "en": f"{payload.member.mention}, ..."},
                     delete_after=5, target=payload.member.id
                )
                return
            else:
                self.cooldown[payload.member.id] = now

            if channel:
                # もし既にチケットチャンネルが作られているならreturnする。
                await payload.message.send(
                    {"ja": (f"{payload.member.mention}, "
                            + "あなたは既にチケットチャンネルを作成しています。"),
                     "en": (f"{payload.member.mention}, "
                            + "...")},
                    delete_after=5, target=payload.member.id
                )
                return
            # チケットチャンネルの作成に必要な情報を集める。
            role = (payload.message.guild.get_role(int(payload.message.content[11:]))
                    if len(payload.message.content) > 15
                    else None)
            # overwritesを作る。
            perms = {
                payload.message.guild.default_role: discord.PermissionOverwrite(read_messages=False)
            }
            if role:
                # もしroleが指定されているならroleもoverwritesに追加する。
                perms[role] = discord.PermissionOverwrite(read_messages=True)
            # チケットチャンネルを作成する。
            channel = await payload.message.channel.category.create_text_channel(
                channel_name, overwrites=perms
            )
            await channel.send(
                {"ja": f"{payload.member.mention}, ここがあなたのチャンネルです。",
                 "en": f"{payload.member.mention}, ..."},
                target=payload.member.id
            )
        else:
            # もしリアクションが削除されたなら。
            if channel:
                # 既ににリアクションチャンネルを作っている人ならチャンネルを削除する。
                await channel.delete()

    @commands.Cog.listener()
    async def on_full_reaction_add(self, payload):
        await self.on_full_reaction(payload)

    @commands.Cog.listener()
    async def on_full_reaction_remove(self, payload):
        await self.on_full_reaction(payload)


def setup(bot):
    bot.add_cog(Ticket(bot))
