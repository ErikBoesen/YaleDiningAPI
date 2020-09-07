from app import app, db, celery
from app.models import Location, Manager

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
        'version': 3,
    }
    r = requests.get(FASTTRACK_ROOT + 'locations.cfm', params=params)
    data = r.json()
    # Restructure data into a list of dictionaries for easier manipulation
    data = [
        {data['COLUMNS'][index]: entry[index] for index in range(len(entry))}
        for entry in data['DATA']
    ]
    Location.query.delete()
    Manager.query.delete()
    for raw in data:
        location = Location(
            id=int(raw['ID_LOCATION']),
            code=int(raw['LOCATIONCODE']),
            name=raw['DININGLOCATIONNAME'],
            type=raw['TYPE'],
            capacity=raw['CAPACITY'],
            is_open=not bool(raw['ISCLOSED']),
            address=raw['ADDRESS'],
            phone=raw['PHONE'],
        )
        geolocation = raw.get('GEOLOCATION')
        if geolocation is not None:
            location.latitude, location.longitude = [float(coordinate) for coordinate in geolocation.split(',')]
        db.session.add(location)
        num_managers = 0
        while num_managers < 4:
            num_managers += 1
            name = raw[f'MANAGER{num_managers}NAME']
            email = raw[f'MANAGER{num_managers}EMAIL']
            if name is not None and email is not None:
                manager = Manager(name=name, email=email)
                manager.location = location
                db.session.add(location)
    db.session.commit()
