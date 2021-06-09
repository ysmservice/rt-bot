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


worker.run()
