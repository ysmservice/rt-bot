from discord.ext import commands
import discord
from time import time

class Database:
    def __init__(self, bot):
        self.db = bot.mysql
        self.bot = bot

    async def get_channel(self, guildid:int):
        async with self.db.get_cursor() as c:
            data = await c.get_data("rta", {"guild": guildid})
        if data is not None:
            return self.bot.get_channel(int(data[1]))

    async def first_setup(self):
        async def self.db.get_cursor() as c:
            await c.create_table("rta", {"guild": "BIGINT", "channel": "BIGINT"})

    async def set_rta(self, guildid:int, channelid:int):
        async with self.db.get_cursor() as c:
            await c.insert_data("rta", {"guild": guildid, "channel": channelid})

class RTA(commands.Cog):
    def __init__(self, bot):
        self.users = {}
        self.db = Database(bot)

    @commands.group(
    extras={
            "headding": {
                "ja": "即抜けRTA通知",
                "en": "leaving RTA notification"
            }, "parent": "ServerUseful"
        },
    aliases=["RTA", "あーるてぃーえー", "即抜け",
             "rta_notification", "rta-notification", "RTA-notification", "RTA_notification",
             "rta_notice", "rta-notice", "RTA-notice", "RTA_notice"]
    )
    @commands.has_guild_permissions(kick_members=True)
    async def rta(self, ctx):
        """!lang ja
        -------
        即抜けRTA通知用のコマンドです。
        
        Aliases
        -------
        RTA, あーるてぃーえー, 即抜け, rta_notification, rta_notice
        
        !lang en
        --------
        This is the leaving RTA notification command.

        Aliases
        -------
        RTA, rta_notification, rta_notice
        """
        if ctx.invoked_subcommand is None:
            await ctx.reply("コマンドの使いかたが間違っています。")

    @commands.Cog.listener()
    async def on_full_ready(self):
        await self.db.first_setup()

    @rta.command(aliases=["set", "設定"], headding={
        "ja":"即抜けRTA通知の設定",
        "en":"Set recording RTA channel"
    })
    async def setup(self, ctx, channel:discord.TextChannel=None):
        """!lang ja
        -------
        即抜けRTAを設定します。

        Parameters
        ----------
        channel : チャンネル名かメンション、ID
            通知を行うチャンネルです。
            もしない場合は実行したチャンネルに通知されます。
            
        !lang en
        --------
        Set channel which recording the leaving RTA.
        
        Parameters
        ----------
        channel : channel name, mention, or id
            The notification channel.
            If you don't set the parameter, the RTA will be notified to the executed channel. 
        """
        cid = ctx.channel.id if channel is None else channel.id
        await self.db.set_rta(ctx.guild.id, cid)
        await ctx.reply(embed=discord.Embed(title="成功", description=f"rta通知チャンネルを{channel.mention}にしました。", color=0x00ff00))

    @commands.Cog.listener()
    async def on_member_join(self, member):
        self.users[str(member.id)] = time()

    @commands.Cog.listener()
    async def on_member_leave(self, member):
        if str(member.id) in self.users:
            if time() - self.users[member.id] < 11:
                channel = await self.db.get_channel()
                if channel is not None:
                    embed = discord.Embed(title = "即抜けRTA", description = f"{member}が{round(time() - self.users[member.id], 6)}秒で抜けちゃった。。。")
                    await channel.send(embed = embed)
            member.id


def setup(bot):
    bot.add_cog(RTA(bot))
