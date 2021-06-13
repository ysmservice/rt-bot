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
    print("ああああああああttst", data["content"])


@worker.event()
async def create_message(ws, data):
    print("ああああああああ", data["content"])


@worker.route("/api/check")
async def testweb(data):
    data = worker.web("json", {"status": "ok"})
    return data


worker.run(web=True, web_ws_url="ws://localhost:8080/webserver")
