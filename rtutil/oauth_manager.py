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
        if request.ctx.user is None:
            data["user_name"] = "Unknown"
        else:
            data["user_name"] = str(request.ctx.user)
            data["login"] = True
        return sanic.response.json(data)

    @commands.Cog.route("/account/login")
    @OAuth.login_require()
    async def login(self, request):
        print("loggin", request.ctx.user.name, request.ctx.user.id)
        return sanic.response.redirect("/dashboard.html")

    @commands.Cog.route("/discord/login")
    @OAuth.login_require()
    async def login_alias(self, request):
        await self.login(request)

    @commands.Cog.route("/account/logout")
    async def logout(self, request):
        r = sanic.response.redirect("/")
        if "session" in r.cookies:
            del r.cookies["session"]
        return r

    @commands.Cog.route("/discord/logout")
    async def logout_alias(self, request):
        await self.logout(request)


def setup(bot):
    bot.add_cog(OAuthCog(bot))
