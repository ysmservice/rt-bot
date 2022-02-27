# RT - RT Life

from __future__ import annotations

from asyncio import all_tasks
from time import time

from discord.ext import commands, tasks

from onami.functools import executor_function
from psutil import virtual_memory, cpu_percent

from rtlib import RT


class RTLife(commands.Cog):
    def __init__(self, bot: RT):
        self.data = {
            "botCpu": [], "botMemory": [], "backendCpu": [], "backendMemory": [],
            "users": [], "guilds": [], "backendLatency": [], "discordLatency": [],
            "botPoolSize": [], "botTaskCount": [], "backendPoolSize": [], "backendTaskCount": []
        }
        self.bot = bot
        self.bot.rtws.set_event(self.get_status)
        self.update_status.start()

    @executor_function
    def process_psutil(self) -> tuple[float, float]:
        return virtual_memory().percent, cpu_percent(interval=1)

    @tasks.loop(seconds=5)
    # @tasks.loop(minutes=10)
    async def update_status(self):
        server_status = await self.process_psutil()
        try: data = await self.bot.rtc.request("get_backend_status", None)
        except: data = ((0, 0), (4, 30))
        for key in self.data.keys():
            if key == "botMemory":
                self.data[key].append(server_status[0])
            elif key == "botCpu":
                self.data[key].append(server_status[1])
            elif key == "users":
                self.data[key].append(len(self.bot.users))
            elif key == "guilds":
                self.data[key].append(len(self.bot.guilds))
            elif key == "backendLatency":
                if self.bot.backend:
                    latency = time()
                    async with self.bot.session.get(
                        f"{self.bot.get_url()}/api/ping"
                    ) as r:
                        if await r.text() == "pong":
                            latency = round((time() - latency) * 1000, 1)
                        elif self.data[key]:
                            latency = self.data[key][-1]
                        else:
                            latency = 0.0
                else:
                    latency = self.data[key][-1] if self.data[key] else 0.0
                self.data[key].append(latency)
            elif key == "discordLatency":
                self.data[key].append(round(self.bot.latency * 1000, 1))
            elif key == "botPoolSize":
                self.data[key].append(self.bot.mysql.pool.size)
            elif key == "botTaskCount":
                self.data[key].append(len(all_tasks()))
            elif key == "backendPoolSize":
                self.data[key].append(data[0][0])
            elif key == "backendTaskCount":
                self.data[key].append(data[0][1])
            elif key == "backendMemory":
                self.data[key].append(data[1][0])
            elif key == "backendCpu":
                self.data[key].append(data[1][1])
            if len(self.data[key]) >= 10008:
                del self.data[key]

    def get_status(self, _):
        return self.data

    def cog_unload(self):
        self.update_status.cancel()


def setup(bot):
    bot.add_cog(RTLife(bot))