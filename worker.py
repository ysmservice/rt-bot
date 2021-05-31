# RT - Worker Program

import rtutil


worker = rtutil.Worker("r2!")


@worker.command()
async def test(ws, data, ctx):
    print(data["content"])
    # r2!test 1


worker.run()
