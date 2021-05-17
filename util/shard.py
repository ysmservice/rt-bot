# RT - Shard

import discord

from multiprocessing import Pool, Queue
import asyncio


class Worker(discord.Client):
    def __init__(self):
        self.Super.__init__(loop=asyncio.new_event_loop())

    async def listening_event(self, token: str, queue):
        self.login(token)
        while True:
            for event_type, data in :
                if event_type == "stop_worker":
                    break
                if event_type == "on_message":
                    print(data["content"])

        self.close()


class RTShardClient(discord.AutoShardedClient):
    def __init__(self, default_worker_count: int, max_worker: int,  *args, **kwargs):
        # workerを動かす。
        pool = Pool(max_worker)
        self.queue = Queue()
        for _ in range(default_worker_count):
            worker = Worker(self.data.token)
            pool.apply_async(target_worker.listening_event,
                             args=(self.data["token"], self.queue))
        pool.close()

        self.Super().__init__(*args, **kwargs)

    async def on_message(self, message):
        data = {
            "message": message,
            "guild": message.guild,
            "channel": message.channel,
            "author": message.author,
            "content": message.content,
            "clean_content": message.clean_content
        }

        self.queue.put(["on_message", data])
