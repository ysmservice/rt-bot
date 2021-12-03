# RT落ちの情報収集ためのロガー

import discord
import logging


def setup(bot):

    logger = logging.getLogger('discord')
    logger.setLevel(logging.DEBUG)
    handler = logging.handlers.RotatingFileHandler(
        filename='log/discord.log', encoding='utf-8', mode='w',
        maxBytes=10000000, backupCount=50
    )
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    logger.addHandler(handler)
