# RT - Favicon.ico Redirect

from sanic.response import redirect


def setup(bot):
    try:
        @bot.web.route("/favicon.ico")
        async def favicon_redirect(request):
            return redirect("/img/favicon.ico")
    except Exception as e:
        if bot.test:
            print("Error on favicon redirect:", e)