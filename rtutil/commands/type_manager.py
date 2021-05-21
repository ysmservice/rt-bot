# RT - Type Manager

import discord


class TypeManager():
    def channel_to_dict(self, channel):
        return {
            "name": channel.name,
            "id": channel.id
        }

    def user_to_dict(self, user):
        return {
            "name": user.name,
            "id": user.id
        }

    def member_to_dict(self, member):
        return {
            "name": member.name,
            "guild": self.guild_to_dict(member.guild),
            "id": member.id
        }

    def guild_to_dict(self, guild):
        return {
            "name": guild.name,
            "id": guild.id,
            "channels": [self.channel_to_dict(channel) 
                          for channel in guild.channels],
            "members": [self.member_to_dict(member)
                         for member in guild.members]
        }

    def message_to_dict(self, message):
        return {
            "message": {
                "content": message.content,
                "clean_content": message.clean_content,
                "channel": self.channel_to_dict(message.channel),
                "guild": self.guild_to_dict(message.guild),
                "author": self.member_to_dict(message.author)
            }
        }
