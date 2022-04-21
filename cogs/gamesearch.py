# Free RT - gamesearch

from discord.ext import commands
import aiohttp
import urllib.parse
import discord
import json

class gamesearch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="gamesearch")
    async def transit(self, ctx, *, name):
        async with self.bot.session.get("https://ysmsrv.wjg.jp/disbot/gamesearch.php?q="+urllib.parse.quote_plus(name, encoding='utf-8')) as resp:
            sid = await resp.text()
            gj = json.loads(sid)
            hdw = ""
            try:
               game = gj["Items"][0]
               gametitle = game["Item"]["titleKana"]
               for item in gj["Items"]:
                  if gametitle in item["Item"]["titleKana"]:
                     hdw = hdw + " " + item["Item"]["hardware"]
               embed = discord.Embed(title=gametitle + "の詳細", description=game["Item"]["itemCaption"].replace('\\n','\n'), color=0x0066ff)
               embed.add_field(name="機種", value=hdw)
               embed.set_image(url=game["Item"]["largeImageUrl"])
               embed.set_footer(text="ゲーム情報検索")
               await ctx.send(embed=embed)
            except IndexError:
               await ctx.send("すみません。見つかりませんでした。別の単語をお試しください")



def setup(bot):
    return bot.add_cog(gamesearch(bot))
