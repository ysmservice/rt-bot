# RT - Worker Program

import rtutil
from ujson import dumps, loads


worker = rtutil.Worker("r2!")


@worker.command()
async def test(self, ws, data):
    print("hi")


worker.run()
