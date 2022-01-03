from discord.ext import commands
import discord
from time import time

class Database:
    def __init__(self, bot):
        self.db = bot.db
        self.bot = bot
        
    async def get_channel(self, guildid:int):
        async with self.db.get_cursor() as c:
            data = await c.get_data("rta", {"guild": guildid})
        if data is not None:
            return self.bot.get_channel(int(data[1]))
    
    async def set_rta(self, guildid:int, channelid:int):
        async with self.db.get_cursor() as c:
            await c.insert_data("rta", {"guild": guildid, "channel": channelid})

class RTA(commands.Cog):
    def __init__(self, bot):
        self.users = {}
        self.db = Database(bot)
        
    @commands.group()
    async def rta(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send("間違っています")
            
    @rta.command()
    async def setup(self, ctx, channel:discord.TextChannel):
        await self.db.set_rta(ctx.guild.id, channel.id)
        await ctx.send("success")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        self.users[member.id] = time()
        
    @commands.Cog.listener()
    async def on_member_leave(self, member):
        if member.id in self.users:
            if time() - self.users[member.id] < 11:
                channel = await self.db.get_channel()
                if channel is not None:
                    embed = discord.Embed(title = "即抜けRTA", description = f"{round(time() - self.users[member.id], 6)秒で抜けちゃった。。。"
                    await channel.send(embed = embed)
                        
            
def setup(bot):
    bot.add_cog(RTA(bot))
