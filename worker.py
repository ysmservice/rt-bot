# RT - Worker Program

import logging
import rtutil


test = True
if test:
    prefixes = ("r2!", "R2!", "#2 ", ".2 ")
else:
    prefixes = ("rt!", "RT!", "#t ", "#T ", ".t ", ".T ")


worker = rtutil.Worker(prefixes, logging_level=logging.DEBUG)


@worker.command()
async def test(ws, data, ctx):
    print(data["content"])
    # r2!test 1


@worker.route("/test")
async def testweb(data):
    data = worker.web("template", "index.html")
    print(data)
    return data


worker.run(web=True, ws_url="ws://localhost:8080/webserver")
