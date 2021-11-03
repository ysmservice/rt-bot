# rtutil - OAuth Manager

from discord.ext import commands

from data import get_headers
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
            data["icon_url"] = None
        else:
            data["user_name"] = str(request.ctx.user)
            data["icon_url"] = (
                str(request.ctx.user.avatar.url)
                if request.ctx.user.avatar
                else "http://tasuren.syanari.com/RT/Discord.jpg"
            )
            data["login"] = True
        return sanic.response.json(
            data, headers=get_headers(self.bot, request)
        )

    @commands.Cog.route("/account/login")
    @OAuth.login_require()
    async def login(self, request):
        return sanic.response.redirect("/dashboard.html")

    @commands.Cog.route("/discord/login")
    @OAuth.login_require()
    async def login_alias(self, request):
        return await self.login(request)

    @commands.Cog.route("/account/logout")
    async def logout(self, request):
        r = sanic.response.redirect("/")
        if "session" in r.cookies:
            del r.cookies["session"]
        return r

    @commands.Cog.route("/discord/logout")
    async def logout_alias(self, request):
        return await self.logout(request)


def setup(bot):
    return
    bot.add_cog(OAuthCog(bot))
