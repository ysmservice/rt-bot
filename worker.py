# RT - Worker Program

import rtutil
from ujson import dumps, loads


worker = rtutil.Worker()


@worker.event
async def on_message(ws, data):
    if data["content"] == "r2!test":
        callback_data = data["callback_template"]
        callback_data["type"] = "discord"
        callback_data["data"]["type"] = "send"
        callback_data["data"]["args"] = ["From worker"]
        await ws.send(dumps(callback_data))
        data = loads(await ws.recv())


worker.run()
