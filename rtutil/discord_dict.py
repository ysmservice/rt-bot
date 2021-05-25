# RT - Discord to Dictionary


def channel(target_channel):
    return {
        "name": target_channel.name,
        "id": target_channel.id
    }


def text_channel(target_channel):
    data = channel(target_channel)


def message(message):
    data = {
        "content": message.content,
        "clean_content": message.clean_content,
        "author": (member(message.author)
                   if message.guild else user(message.author)),
        "channel": text_channel(message.channel),
        "guild": guild(message.guild)
    }
