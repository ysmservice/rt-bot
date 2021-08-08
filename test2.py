import requests, json


ITEMS = {
    "text": "text",
    "check": "checked",
    "radios": "radios"
}


cookies = dict(session="ciYRAyZQ=3yl2kXjJI1yiczM0ejNyNzNVTNozM2jwkMjwIimb5St6ZEII1iFMnh4WVf=")
data = requests.get("http://localhost/api/settings/guild", cookies=cookies)
data = data.json()
print(data)
new_data = {}


for guild_id in data["settings"]:
    print("Guild:", data["settings"][guild_id]["name"])
    for command_name in data["settings"][guild_id]["commands"]:
        print(" ", command_name)
        new_data[command_name] = {}
        for item_name in data["settings"][guild_id]["commands"][command_name]["items"]:
            new_data[command_name][item_name] = {
                "item_type": data["settings"][guild_id]["commands"][command_name]["items"][item_name]["item_type"],
                ITEMS[data["settings"][guild_id]["commands"][command_name]["items"][item_name]["item_type"]]: "New"
            }
    break


print("Posting...", new_data)
r = requests.post("http://localhost/api/settings/update/guild/" + str(guild_id), cookies=cookies, data=json.dumps(new_data))
print("Done.", r.text)