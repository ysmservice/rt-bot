# RT - Bot General

import rtutil
from discord.ext import tasks

from logging import getLogger


TEAM_MEMBERS = """<:yaakiyu:731263096454119464> Yaakiyu [SERVER](https://discord.gg/wAkahzZ)
<:takkun:731263181586169857> Takkun#1643 [SERVER](https://discord.gg/VX7ceJw)
<:tasren:731263470636498954> tasuren#5161 [WEBSITE](http://tasuren.f5.si)
<:Snavy:788377881092161577> Snavy#2853 [SERVER](https://discord.gg/t8fsvk3)"""
STATUS_BASE = ("rt!help | {} users", "rt!help | {} servers")


class BotGeneral(metaclass=rtutil.Cog):
    def __init__(self, worker):
        self.worker = worker
        self.now_status = 0
        self.logger = getLogger("rt.worker.BotGeneral")
        self.status_updater.start()

    @tasks.loop(seconds=120)
    async def status_updater(self):
        await self.worker.wait_until_ready()
        if (await self.worker.number())["index"] != 0:
            if self.now_status:
                setting_word = await self.worker.discord(
                    "users", get_length=True, wait=True)
                self.now_status = 0
            else:
                setting_word = await self.worker.discord(
                    "guilds", get_length=True, wait=True)
                self.now_status = 1
            status_text = STATUS_BASE[self.now_status].format(setting_word)
            await self.worker.discord(
                "change_presence", activity=((status_text,),), status="idle")
            self.logger.info("Updated status presence.")

    def cog_unload(self):
        if self.worker.number == 0:
            self.status_updater.stop()


def setup(worker):
    worker.add_cog(BotGeneral(worker))
