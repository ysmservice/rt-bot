"""Cogの追加/削除時に呼び出される`on_cog_add/remove`というイベントを作るためのエクステンションです。  
`bot.load_extension("util.ext.on_cog_add")`で有効化することができます。  
また`util.setup(bot)`でも有効化することができます。

# Examples
```python
@bot.event
async def on_cog_add(cog):
    print("Added cog", cog.__name__)

@bot.event
async def on_cog_remove(cog):
    print("Removed cog", cog.__name__)
```"""

from discord.ext import commands


class OnCogAdd(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _add_cog(self, cog, **kwargs):
        self.bot.dispatch("cog_add", cog)

    def _remove_cog(self, name):
        cog = self.bot.cogs[name]
        self.bot.dispatch("cog_remove", cog)


async def setup(bot):
    await bot.add_cog(OnCogAdd(bot))
