import requests
import time
import json

# Temporary place to store all collected data
colleges = {}

# Parse JAMIX data
JAMIX_ROOT = 'https://usa.jamix.cloud/menu/app'
UIDL_ENDPOINT = 'https://usa.jamix.cloud/menu/UIDL/?v-uiId=20'
headers = {
    'Content-type': 'application/json; charset=UTF-8',
    'Cookie': 'JSESSIONID=B8E6DC9EE2470B2607CFD8844923057D.tomcatCustomer',
}

###################################################
# Perform initial request to get the college's page
params = {
    # Institution identifier
    'anro': 97939,
    # College identifier
    'k': 1,
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
uiid = data['v-uiId']
data_uidl = json.loads(data['uidl'])
csrf_token = data_uidl['Vaadin-Security-Key']
state = data_uidl['state']
# 0th element should be the title
assert(state['0']['pageState']['title'] == 'JAMIX MENU')
college = state['8']['text']
print(json.dumps(state))
print('Parsed initial page for ' + college)

# Passed as clientId and syncId, incremented everytime we make a UIDL request
requests_made = 0

PID_PREVIOUS_DAY = '9'
#######################################
# Go leftward until running out of days
while True:
    params = {
        'v-uiId': uiid
    }
    requests_made += 1
    payload = {
        'clientId': requests_made,
        'syncId': requests_made,
        'csrfToken': csrf_token,
        'rpc': [
            [
                PID_PREVIOUS_DAY,
                'com.vaadin.shared.ui.button.ButtonServerRpc',
                'click',
                [
                    {
                        'altKey': False,
                        'button': 'LEFT',
                        'clientX': 189,
                        'clientY': 51,
                        'ctrlKey': False,
                        'metaKey': False,
                        'relativeX': 41,
                        'relativeY': 16,
                        'shiftKey': False,
                        'type': 1
                    }
                ]
            ]
        ]
    }
    r = requests.post('https://usa.jamix.cloud/menu/UIDL/', payload, params=params, headers=headers)
    print(r.text)
    break
