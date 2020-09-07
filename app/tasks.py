from app import app, db, celery
from app.models import Student

import os
import requests
import re
from bs4 import BeautifulSoup
from yaledining import YaleDining as FastTrackAPI


@celery.task
def scrape():
    # Old FastTrack-based dining API, which still provides non-menu data
    ft = FastTrackAPI()
    locations = ft.locations()
    for
