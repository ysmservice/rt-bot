import requests, json


ITEMS = {
    "text": "text",
    "check": "checked",
    "radios": "radios"
}
BASE = "localhost"


cookies = dict(session="ciYRAyZQ=3yl2kXjJI1yiczM0ejNyNzNVTNozM2jwkMjwIimb5St6ZEII1iFMnh4WVf=")
data = requests.get(f"http://{BASE}/api/settings/user", cookies=cookies)
print(data.text)
data = data.json()
new_data = {}


for command_name in data["settings"]:
    print(" ", command_name)
    new_data[command_name] = {}
    for item_name in data["settings"][command_name]["items"]:
        if item_name == "radios_1":
            result = {
                "radio1": False,
                "radio2": True
            }
        else:
            result = "New!"
        new_data[command_name][item_name] = {
            "item_type": data["settings"][command_name]["items"][item_name]["item_type"],
            ITEMS[data["settings"][command_name]["items"][item_name]["item_type"]]: result
        }


print("Posting...", new_data)
r = requests.post(f"http://{BASE}/api/settings/update/user", cookies=cookies, data=json.dumps(new_data))
print("Done.", r.text)
