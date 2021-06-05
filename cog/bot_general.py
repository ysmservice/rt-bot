# RT - Bot General

import rtutil
from discord.ext import tasks


TEAM_MEMBERS = """<:yaakiyu:731263096454119464> Yaakiyu [SERVER](https://discord.gg/wAkahzZ)
<:takkun:731263181586169857> Takkun#1643 [SERVER](https://discord.gg/VX7ceJw)
<:tasren:731263470636498954> tasuren#5161 [WEBSITE](http://tasuren.f5.si)
<:Snavy:788377881092161577> Snavy#2853 [SERVER](https://discord.gg/t8fsvk3)"""
STATUS_BASE = ("rt!help | {} users", "rt!help | {} servers")


class BotGeneral(metaclass=rtutil.Cog):
    def __init__(self, worker):
        self.worker = worker
        self.now_status = 0
        self.status_updater.start()

    @tasks.loop(seconds=120)
    async def status_updater(self):
        if self.now_status:
            setting_word, self.now_status = len(self.bot.users), 0
        else:
            setting_word, self.now_status = len(self.bot.guilds), 1
        status_text = STATUS_BASE[self.now_status].format(setting_word)
        await self.worker.discord(
            "change_presense", activity_base=((status_text,),), status="idle")

    def cog_unload(self):
        self.status_updater.stop()


def setup(worker):
    worker.add_cog(BotGeneral(worker))
