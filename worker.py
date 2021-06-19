# RT - Worker Program

from ujson import load
import logging
import rtutil


test = True
if test:
    prefixes = ("r2!", "R2!", "#2 ", ".2 ")
else:
    prefixes = ("rt!", "RT!", "#t ", "#T ", ".t ", ".T ")


worker = rtutil.Worker(prefixes, logging_level=logging.DEBUG)
worker.load_extension("cog.help")


with open("data.json", "r") as f:
    worker.data = load(f)
worker.colors = {
	key: eval(worker.data["colors"][key]) for key in worker.data["colors"]
}


worker.run(web=True, web_ws_url="ws://localhost:5000/webserver")
