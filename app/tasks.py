from app import app, db, celery
from app.models import Student

import os
import requests
import re
from bs4 import BeautifulSoup


@celery.task
def scrape():
    # Reach out to old FastTrack-based dining API,
    # which still provides non-menu data
    FASTTRACK_ROOT = 'https://www.yaledining.org/fasttrack/'
    params = {
        'version': self.API_VERSION,
    }
    r = requests.get(FASTTRACK_ROOT + 'locations.cfm', params=params)
    data = request.json()
    # Restructure data into a list of dictionaries for easier manipulation
    data = [
        {data['COLUMNS'][index]: entry[index] for index in range(len(entry))}
        for entry in data['DATA']
    ]
    Location.query.delete()
    for raw in data:
