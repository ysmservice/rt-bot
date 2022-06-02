# Free RT Data - URL Requesting Headers

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) " \
             "Chrome/95.0.4638.54 Safari/537.36 Edg/95.0.1020.40"


TWITTERID_HEADERS = {
    "authority": "tweeterid.com",
    "sec-ch-ua": "^\\^Microsoft",
    "accept": "*/*",
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    "x-requested-with": "XMLHttpRequest",
    "sec-ch-ua-mobile": "?0",
    "user-agent": USER_AGENT,
    "sec-ch-ua-platform": "^\\^Windows^\\^",
    "origin": "https://tweeterid.com",
    "sec-fetch-site": "same-origin",
    "sec-fetch-mode": "cors",
    "sec-fetch-dest": "empty",
    "referer": "https://tweeterid.com/",
    "accept-language": "ja,en;q=0.9,en-GB;q=0.8,en-US;q=0.7",
}


YAHOO_SEARCH_HEADERS = {
    'User-Agent': USER_AGENT
}


SECURL_HEADERS = {
    "Connection": "keep-alive",
    "sec-ch-ua": '"Microsoft Edge";v="95", "Chromium";v="95", ";Not A Brand";v="99"',
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "sec-ch-ua-mobile": "?0",
    "User-Agent": USER_AGENT,
    "sec-ch-ua-platform": '"macOS"',
    "Origin": "https://securl.nu",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
    "Referer": "https://securl.nu/",
    "Accept-Language": "ja,en;q=0.9,en-GB;q=0.8,en-US;q=0.7",
}
