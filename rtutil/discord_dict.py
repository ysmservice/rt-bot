# RT - Discord to Dictionary

def message(message):
    data = {
        "content": message.content,
        "clean_content": message.clean_content,
        "author": member(message.author),
        "channel": text_channel(message.channel),
        "guild": guild(message.guild)
    }
