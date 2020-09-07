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
    FASTTRACK_ROOT =
    r = requests.get(FASTTRACK_ROOT + 'locations.cfm'
    for
