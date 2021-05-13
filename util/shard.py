# RT - Shard

import asyincio
from aio_pika import connect, Message, DeliveryMode

from util.worker import run


class ShardManager():
    def __init__(self, bot, worker_count: int = 10):
        self.bot = bot
        self.workers = []

        # 
        for _ in range(worker_count):
             self.worker.append(bot.loop.create_task(run(bot)))
