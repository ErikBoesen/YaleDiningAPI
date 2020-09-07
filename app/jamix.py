import requests
import time
import json

# Parse JAMIX data
JAMIX_ROOT = 'https://usa.jamix.cloud/menu/app'
UIDL_ENDPOINT = 'https://usa.jamix.cloud/menu/UIDL/?v-uiId=20'
params = {
    # Institution identifier
    'anro': 97939,
    # College identifier
    'k': 1,
}
headers = {
}

# Add timestamp parameter
timestamp = int(time.time() * 1000)
params['v-' + str(timestamp)] = ''
payload = {
    'v-browserDetails': 1,
    'theme': 'menu',
    'v-appId': 'menu-3347807',
    'v-sh': 800,
    'v-sw': 1280,
    'v-cw': 707,
    'v-ch': 698,
    'v-curdate': timestamp,
    # TODO; use NY tz
    'v-tzo': 360,
    'v-dstd': 60,
    'v-rtzo': 420,
    'v-dston': True,
    # TODO: use NY tz
    'v-tzid': 'America/Denver',
    'v-vw': 707,
    'v-vh': 698,
    'v-loc': JAMIX_ROOT + '?anro=97939&k=1',
    'v-wn': 'menu-3347807-0.5009829498008829',
}
r = requests.post(JAMIX_ROOT, payload, params=params)
data = r.json()
ui_id = data['v-uiId']
data_uidl = json.loads(data['uidl'])
csrf_token = data_uidl['Vaadin-Security-Key']
state = data_uidl['state']
# 0th element should be the title
assert(state['0']['pageState']['title'] == 'JAMIX MENU')

import sys;sys.exit(0)

params = {
    'v-uiId': 14
}
headers = {
    'Cookie': 'JSESSIONID=B8E6DC9EE2470B2607CFD8844923057D.tomcatCustomer',
}
r = requests.post('https://usa.jamix.cloud/menu/UIDL/', headers=headers, params=params)
print(r.text)
