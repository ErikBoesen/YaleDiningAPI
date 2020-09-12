from app import app, db, celery
from app.models import Location, Manager, Meal, Course, Item, Nutrition

import os
import requests
import json
import datetime
import re
from bs4 import BeautifulSoup

DATE_FMT = '%A, %B %d, %Y'


def read_nutrition_facts(raw):
    nutrition = Nutrition(
        portion_size=raw.pop('Portion Size', None),
    )
    for key in raw:
        snaked_key = key.lower().replace(' ', '_')
        setattr(nutrition, snaked_key, raw[key]['amount'])
        setattr(nutrition, snaked_key + '_pdv', raw[key].get('percent_daily_value'))
    return nutrition


def scrape_fasttrack():
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
            # TODO: I can't figure out what this is for, so just omit it for now.
            #code=int(raw['LOCATIONCODE']),
            name=raw['DININGLOCATIONNAME'],
            type=raw['TYPE'],
            capacity=raw['CAPACITY'],
            is_open=not bool(raw['ISCLOSED']),
            address=raw['ADDRESS'],
            phone=raw['PHONE'],
        )
        print('Parsing ' + location.name)
        geolocation = raw.get('GEOLOCATION')
        if geolocation is not None:
            location.latitude, location.longitude = [float(coordinate) for coordinate in geolocation.split(',')]
        db.session.add(location)
        """
        num_managers = 0
        while num_managers < 4:
            num_managers += 1
            name = raw[f'MANAGER{num_managers}NAME']
            email = raw[f'MANAGER{num_managers}EMAIL']
            if name is not None and email is not None:
                manager = Manager(name=name, email=email)
                manager.location = location
                db.session.add(location)
        """
    print('Done reading FastTrack data.')


def scrape_managers():
    print('Scraping managers.')
    ROOT = 'https://hospitality.yale.edu/residential-dining/'
    locations = Location.query.filter_by(type='Residential').all()
    HEADER_RE = re.compile(r'Management Team')
    for location in locations:
        slug = location.name.lower().replace(' ', '-')
        custom_slugs = {
            'franklin': 'benjamin-franklin',
            'stiles': 'ezra-stiles',
        }
        if slug in custom_slugs:
            slug = custom_slugs[slug]
        print(slug)
        r = requests.get(ROOT + slug)
        soup = BeautifulSoup(r.text, 'html.parser')
        h2 = soup.find('h2', text=HEADER_RE)
        ul = h2.find_next()
        if ul.name == 'p':
            to_scan = [ul]
        elif ul.name == 'ul':
            to_scan = ul.find_all('li')
        for li in to_scan:
            contents = li.contents
            print(contents)
            manager = Manager()
            if len(contents) == 1:
                # The name is not a link, so no email is available
                manager.name, manager.position = contents[0].split(', ')
            elif len(contents) == 2:
                manager.name = contents[0].text
                manager.email = contents[0]['href'].replace('mailto:', '')
                manager.position = contents[1].lstrip(', ').replace('/ ', '/')
            db.session.add(manager)
            manager.location = location
            print('Name: ' + manager.name)
            print('Email: %s' % manager.email)
            print('Position: %s' % manager.position)
    db.session.commit()


def scrape_jamix():
    Meal.query.delete()
    Course.query.delete()
    Item.query.delete()
    Nutrition.query.delete()
    # TODO: find a new way of getting this data in the future.
    with open('app/menus.json', 'r') as f:
        menus = json.load(f)

    # Separate multi-college menus
    # TODO: should we do this at request time?
    # Extract key names to prevent size from changing during iteration
    colleges = list(menus.keys())
    for key in colleges:
        if key == 'Branford and Saybrook':
            value = menus.pop(key)
            menus['Branford'] = value
            menus['Saybrook'] = value
        # Murray & Franklin, Ezra Stiles & Morse
        elif ' & ' in key:
            value = menus.pop(key)
            college_a, college_b = key.split(' & ')
            menus[college_a] = value
            menus[college_b] = value

    print('Reading in menu data.')
    for college in menus:
        print('Parsing college ' + college)
        for day_d in menus[college]:
            # There is no elegance here. Only sleep deprivation and regret.
            date = datetime.datetime.strptime(day_d['date'], DATE_FMT).date()
            print('Parsing day ' + day_d['date'])
            for meal_d in day_d['meals']:
                meal_name = meal_d['name']
                print('Parsing meal ' + meal_name)
                meal = Meal(
                    name=meal_name,
                    date=date,
                )
                meal.location = Location.query.filter_by(name=college).first()
                for course_d in meal_d['courses']:
                    course_name = course_d['name']
                    print('Parsing course ' + course_name)
                    course = Course(
                        name=course_name,
                    )
                    course.meal = meal
                    # Note that both ingredients and nutrition_facts['items'] are dictionaries,
                    # with the keys being the names of the items.
                    ingredients = course_d['ingredients']
                    nutrition_facts = course_d['nutrition_facts']
                    for item_name in ingredients:
                        print('Parsing item ' + item_name)
                        item = Item(
                            name=item_name,
                            ingredients=ingredients[item_name]['ingredients'],
                        )
                        diets = ingredients[item_name]['diets'].split(', ')
                        item.vegan = ('V' in diets)
                        item.vegetarian = ('VG' in diets)
                        allergens = ingredients[item_name].get('allergens')
                        if allergens:
                            allergens = allergens.split(', ')
                            for allergen in allergens:
                                setattr(item, allergen.lower(), True)

                        # TODO: this should always be present, but handle its absence in case the scraper broke
                        if nutrition_facts['items'].get(item_name):
                            # Read nutrition facts
                            # TODO: 'nutrition' or 'nutrition facts'?
                            nutrition = read_nutrition_facts(nutrition_facts['items'][item_name])
                            db.session.add(nutrition)
                            item.nutrition = nutrition
                        item.course = course
                        item.meal = meal
                        db.session.add(item)
                    #course_nutrition = read_nutrition_facts(nutrition_facts['course'])
                    #db.session.add(course_nutrition)
                    # TODO actually add to course!!!!!!!
                    db.session.add(course)
                db.session.add(meal)
    db.session.commit()
    print('Done.')

@celery.task
def scrape():
    scrape_fasttrack()
    scrape_managers()
    scrape_jamix()
