from discord.ext import commands
import discord

class Autopublic(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild or message.author.bot or not message.channel.topic:
            return
        for line in message.channel.topic.splitlines():
            if line.startswith("rt>autopublic"):
                await message.publish()
                await message.add_reaction("✅")
                
def setup(bot):
    bot.add_cog(Autopublic(bot))
