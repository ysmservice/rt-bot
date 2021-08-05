# rtutil - OAuth Manager

from discord.ext import commands
from rtlib import OAuth
import sanic


class OAuthCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.route("/account")
    @OAuth.login_want()
    async def account(self, request):
        data = {
            "login": False,
            "status": "ok"
        }
        if request.user is None:
            data["user_name"] = "Unknown"
        else:
            data["user_name"] = str(request.user)
        return sanic.response.json(data)

    @commands.Cog.route("/discord/login")
    @OAuth.login_require()
    async def login(self, request):
        print("loggin", request.user.name, request.user.id)
        return sanic.response.redirect("/dashboard.html")


def setup(bot):
    bot.add_cog(OAuthCog(bot))