from discord.ext import commands
import discord
from asyncio import sleep

CHP_HELP = {
    "ja": ("メッセージ自動公開機能。",
"""# メッセージ自動公開プラグイン - autopublic
これは`rt>autopublic <optionでcheck>`をニュースチャンネルのトピックに入れることで自動的にメッセージを公開してくれる機能です。  
例：`rt>autopublic` (これをトピックに入れたチャンネルに送信したメッセージは全てメッセージを公開してくれます)
例: `rt>autopublic ckeck` (これをトピックに入れたチャンネルに送信したメッセージは全てメッセージを公開してくれますが、公開するとメッセージにチェックが入ります)
""")

class Autopublic(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bot.loop.create_task(self.on_command_added())
        
    async def on_command_added(self):
        await sleep(1.5)
        for lang in CHP_HELP:
            self.bot.cogs["DocHelp"].add_help(
                "ChannelPlugin", "AutoPublic",
                lang, *CHP_HELP[lang]
            )
        
    @commands.Cog.listener()
    async def on_message(self, message):
        if not hasattr(message.channel, "topic"):
            return
        if not message.guild or message.author.bot or not message.channel.topic:
            return
        for line in message.channel.topic.splitlines():
            if line.startswith("rt>autopublic"):
                await message.publish()
                if len(line.split()) >= 1:
                    option = line.split()[0]
                    if option == "check":
                        await message.add_reaction("✅")
                
def setup(bot):
    bot.add_cog(Autopublic(bot))
