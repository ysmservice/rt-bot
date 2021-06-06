# RT - Discord Requests Bot

import discord # noqa
from time import mktime


class DiscordRequests:
    def __init__(self, backend):
        self.bot, self.ws = backend, backend.ws

    def emoji(self, emoji) -> dict:
        data = {
            "string": str(emoji),
            "name": emoji.name,
            "id": emoji.id,
            "require_colons": emoji.require_colons,
            "animated": emoji.animated,
            "managed": emoji.managed,
            "guild_id": emoji.guild_id,
            "user": self.user(emoji.user) if emoji.user else None,
            "available": emoji.available,
            "created_at": mktime(emoji.created_at),
            "url": emoji.url
        }
        return data

    def public_flags(self, public_flags):
        data = {
            name: bool(eval("public_flags." + name))
            for name in dir(public_flags)
            if name[:2] != "__"
        }
        return data

    def user(self, user) -> dict:
        data = {
            "name": user.name,
            "id": user.id,
            "discriminator": user.discriminator,
            "bot": user.bot,
            "system": user.system,
            "dm_channel": (self.dm_channel(user.dm_channel)
                           if user.dm_channel else None),
            "avatar": user.avatar.url,
            "avatar_png": user.avatar_url_as(format="png"),
            "color": user.color.to_rgb(),
            "created_at": mktime(user.created_at),
            "default_avatar": user.default_avatar.url,
            "display_name": user.display_name,
            "mention": user.mention,
            "public_flags": self.public_flags(user.public_flags)
        }
        return data

    def member(self, member) -> dict:
        data = self.user(member)
        data["nickname"] = member.nickname
        return data

    def channel(self, channel) -> dict:
        data = {
            "name": channel.name,
            "id": channel.id,
            "guild": self.guild(channel.guild)
        }
        return data

    def text_channel(self, channel) -> dict:
        new_data = {
            "type": "text",
            "nsfw": channel.nsfw
        }
        data = self.channel(channel)
        data.update(new_data)
        return data

    def voice_channel(self, channel) -> dict:
        new_data = {
            "type": "voice"
        }
        data = self.channel(channel)
        data.update(new_data)
        return data

    def role(self, role) -> dict:
        data = {
            "name": role.name,
            "id": role.id,
            "color": role.color
        }
        return role

    def guild(self, guild) -> dict:
        data = {
            "name": guild.name,
            "id": guild.id,
            "roles": [self.role(role) for role in guild.roles]
            "emojis": [self.emoji(emoji) for emoji in guild.emojis],
            "members": [self.member(member) for member in member],
            "channels": [(self.text_channel(channel)
                           if isinstance(channel, discord.TextChannel)
                           else self.voice_channel(channel))
                          for channel in guild.channels]
        }
        text_channels, voice_channels = [], []
        for channel in data["channels"]:
            if channel["type"] == "text":
                text_channels.append(channel)
            else:
                voice_channels.append(channel)
        data["text_channels"] = text_channels
        data["voice_channels"] = voice_channels
        return data

    def channel(self, channel) -> dict:
        data = {
            "name": channel.name,
            "id": channel.id
        }
        return data

    def dm_channel(self, channel):
        data = {}
        data.update(self.channel(channel))
        return data

    def get_guild(self, guild_id):
        return self.guild(self.bot.get_guild(guild_id))

    def get_channel(self, channel_id):
        channel = self.bot.get_channel(channel_id)
        if channel:
            if isinstance(channel, discord.TextChannel):
                return self.text_channel(channel)
            else:
                return self.voice_channel(channel)

    def somes(self, datas, converter, get_length: bool):
        return (len(datas) if get_length else
                [converter(data) for data in datas])

    def users(self, get_length: bool = False):
        return self.somes(self.bot.users, self.user, get_length)

    def guilds(self, get_length: bool = False):
        return self.somes(self.bot.guilds, self.guild, get_length)

    def to_args_kwargs(args) -> tuple:
        if len(args) == 0:
            return (), {}
        elif len(args) == 1:
            return args[0]
        else:
            return args[0], args[1]

    async def change_presence(
            self, *, activity_base="Game", activity=(),
            status="online", afk=False):
        if isinstance(status, str):
            status = eval("discord.Status." + status)
        else:
            raise TypeError("引数のstatusは文字列の必要があります。")
        args, kwargs = self.to_args_kwargs(activity)
        activity = eval("discord." + activity_base)(*args, **kwargs)
        await self.bot.change_presense(
            activity=activity, status=status, afk=afk)
