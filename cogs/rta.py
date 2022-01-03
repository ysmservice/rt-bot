from discord.ext import commands
from time import time

class RTA(commands.Cog):
    def __init__(self):
        self.users = {}

    @commands.Cog.listener()
    async def on_member_join(self, member):
        self.users[member.id] = time()
        
    @commands.Cog.listener()
    async def on_member_leave(self, member):
        if member.id in self.users:
            if time() - self.users[member.id] < 11:
                pass
            
def setup(bot):
    bot.add_cog(RTA(bot))
