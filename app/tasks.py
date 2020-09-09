from app import app, db, celery
from app.models import Location, Manager, Meal, Item, Nutrition

import os
import requests
import json
import datetime
from bs4 import BeautifulSoup

DATE_FMT = '%A, %B %d, %Y'

def read_nutrition_facts(raw):
    nutrition = Nutrition(
        portion_size=raw.pop('Portion Size'),
    )
    for key in raw:
        snaked_key = key.lower().replace(' ', '_')
        setattr(nutrition, snaked_key, raw[key]['amount'])
        setattr(nutrition, snaked_key + '_pdv', raw[key].get('percent_daily_value'))
    return nutrition


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
        print('Parsing ' + location.name)
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
    print('Done reading FastTrack data.')

    # TODO: temporary.

    with open('menus.json', 'r') as f:
        menus = json.load(f)
    for college in menus:
        for day_d in menus[college]:
            # There is no elegance here. Only sleep deprivation and regret.
            date = datetime.datetime.strptime(day_d['date']).date()
            for meal_d in day['meals']:
                meal = Meal(
                    name=meal_d['name'],
                    date=date,
                )
                for course_d in meal_d['courses']:
                    course_name = course_d['name']
                    items = {}
                    # Note that both ingredients and nutrition_facts['items'] are dictionaries,
                    # with the keys being the names of the items. Yeah, I know it sucks.
                    # I'm trying to web scrape an absolutely bewitched Java-based web app at 2:28am. Let me live.
                    ingredients = course_d['ingredients']
                    for item_name in ingredients:
                        items[item_name] = Item(
                            name=item_name,
                            course=course_name,
                            ingredients=ingredients[item_name]['ingredients'],
                        )
                        diets = ingredients[item_name]['diets'].split(', ')
                        items[item_name].vegan = ('V' in diets)
                        items[item_name].vegetarian = ('VG' in diets)
                        allergens = ingredients[item_name].get('allergens')
                        if allergens:
                            allergens = allergens.split(', ')
                            for allergen in allergens:
                                # AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
                                setattr(items[item_name], allergen.lower(), True)
                    course_nutrition = read_nutrition_facts(nutrition_facts['course'])
                    db.session.add(course_nutrition)
                    # TODO actually add to course!!!!!!!
                    nutrition_facts = course_d['nutrition_facts']
                    for item_name in nutrition_facts['items']:
                        # TODO: 'nutrition' or 'nutrition facts'?
                        nutrition = read_nutrition_facts(nutrition_facts['items'][item_name])
                        db.session.add(nutrition)
                        items[item_name].nutrition = nutrition
                    for item_name in items:
                        db.session.add(items[item_name])
                db.session.add(meal)
    db.session.commit()
