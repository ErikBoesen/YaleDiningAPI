from app import app, db, celery
from app.models import Hall, Manager, Meal, Item, Nutrition
from app.mail import send_scraper_report

from celery.schedules import crontab

import os
import requests
import json
import datetime
import pytz
import re
from bs4 import BeautifulSoup
import time
from random import randint
from selenium import webdriver
from selenium.common.exceptions import ElementClickInterceptedException, ElementNotInteractableException

DATE_FMT = '%Y-%m-%d'
DATE_FMT_JAMIX = '%A, %B %d, %Y'
TIME_FMT = '%H:%M'
TIMEZONE = pytz.timezone('America/New_York')
WAIT_PERIOD = 10
MENU_FILE = 'menus.json'
MIN_MEALS_ALLOWED = 2
FASTTRACK_NAME_OVERRIDES = {
    'Franklin': 'Benjamin Franklin',
    'Stiles': 'Ezra Stiles',
}
NICKNAMES = {
    **{name: nickname for nickname, name in FASTTRACK_NAME_OVERRIDES.items()},
    'Grace Hopper': 'Hopper',
    'Jonathan Edwards': 'JE',
    'Pauli Murray': 'Murray',
    'Timothy Dwight': 'TD',
}
JAMIX_HALL_NAMES = {
    **FASTTRACK_NAME_OVERRIDES,
    'Murray': 'Pauli Murray',
    'Hopper': 'Grace Hopper',
    'ESM': 'Ezra Stiles/Morse',
    'JE': 'Jonathan Edwards',
}
HALL_IDS = {
    'Berkeley': 'BK',
    'Branford': 'BR',
    'Davenport': 'DC',
    'Franklin': 'BF',
    'Grace Hopper': 'GH',
    'Jonathan Edwards': 'JE',
    'Morse': 'MC',
    'Pauli Murray': 'MY',
    'Pierson': 'PC',
    'Saybrook': 'SY',
    'Silliman': 'SM',
    'Stiles': 'ES',
    'Timothy Dwight': 'TD',
    'Trumbull': 'TC',
}
MEAL_NAME_OVERRIDES = {
    'OC Dinner': 'Dinner',
    # TODO: check that this error is still happening, as this override could cause problems
    'breakfast': 'Lunch',
}
COURSE_NAME_OVERRIDES = {
    'Yale Bakery Dessert': 'Dessert',
    'Smart Meals (must be ordered ahead)': 'Smart Meals',
}
ITEM_NAME_OVERRIDES = {
    'Nut-Free Basil Pesto (basil, canola oil, extra virgin olive oil, romano cheese, pasteurized sheep\'s milk, rennet, garlic, salt)': 'Nut-Free Basil Pesto',
}

driver = None


def create_driver():
    # TODO: using globals is bad practice.
    global driver

    ops = webdriver.ChromeOptions()
    ops.add_argument('--disable-gpu')
    ops.add_argument('--no-sandbox')
    GOOGLE_CHROME_PATH = os.environ.get('GOOGLE_CHROME_PATH')
    if GOOGLE_CHROME_PATH:
        ops.binary_location = GOOGLE_CHROME_PATH
    CHROMEDRIVER_PATH = os.environ.get('CHROMEDRIVER_PATH', '/usr/local/bin/chromedriver')
    driver = webdriver.Chrome(executable_path=CHROMEDRIVER_PATH, chrome_options=ops)
    driver.maximize_window()
    driver.implicitly_wait(WAIT_PERIOD)


def round_increment(number, increment):
    return round(number / increment) * increment


def round_calories(n) -> int:
    if n is None or n < 5:
        return 0
    elif n <= 50:
        return round_increment(n, 5)
    return round_increment(n, 10)


def split_quantity(quantity):
    if quantity is None:
        return None
    n, unit = quantity.split()
    n = float(n.replace(',', ''))
    return n, unit


def round_fats(quantity) -> str:
    if quantity is None:
        return None
    n, unit = split_quantity(quantity)
    if n < 0.5:
        n = 0
    elif n < 5:
        n = round_increment(n, 0.5)
        if n % 1 == 0:
            n = int(n)
    else:
        n = round_increment(n, 1)
    return str(n) + ' ' + unit


def round_cholesterol(quantity) -> str:
    if quantity is None:
        return None
    n, unit = split_quantity(quantity)
    if n < 2:
        n = 0
    elif n < 5:
        # Here we deviate from the standard slighly.
        # Regularly we'd say "less than 5 mg", but this is a
        # little unpleasant for our interface.
        n = round_increment(n, 1)
    else:
        n = round_increment(n, 5)
    return str(n) + ' ' + unit


def round_sp(quantity) -> str:
    """
    Round Podium and Potassium quantities.
    """
    if quantity is None:
        return None
    n, unit = split_quantity(quantity)
    if n < 5:
        n = 0
    elif n < 140:
        n = round_increment(n, 5)
    else:
        n = round_increment(n, 10)
    return str(n) + ' ' + unit


def round_tdt(quantity) -> str:
    """
    Round Total carbohydrate, Dietary fiber, and Total Sugars quantities
    """
    if quantity is None:
        return None
    n, unit = split_quantity(quantity)
    if n < 1:
        # We deviate from the standard here too; if it's between 0.5-1 we're supposed
        # to say "less than 1 g"
        n = 0
    else:
        n = round_increment(n, 1)
    return str(n) + ' ' + unit


def round_protein(quantity) -> str:
    """
    Round Protein quantities
    """
    if quantity is None:
        return None
    n, unit = split_quantity(quantity)
    if n < 1:
        # We deviate from the standard here too; if it's between 0.5-1 we're supposed
        # to say "less than 1 g"
        n = 0
    else:
        n = round_increment(n, 1)
    return str(n) + ' ' + unit


def round_vm(quantity) -> str:
    """
    Round Vitamin and Mineral quantities
    """
    if quantity is None:
        return None
    n, unit = split_quantity(quantity)
    # We don't do any explicit rounding here, but extra 0s will be trimmed.
    return str(n) + ' ' + unit


def standardize_nutrition(n: Nutrition) -> Nutrition:
    # Perform rounding and correction of fields to adhere to FDA labelling standards.
    # See more on pp129-130: https://www.fda.gov/files/food/published/Food-Labeling-Guide-%28PDF%29.pdf
    n.calories = round_calories(n.calories)
    n.total_fat = round_fats(n.total_fat)
    n.saturated_fat = round_fats(n.saturated_fat)
    n.trans_fat = round_fats(n.trans_fat)
    n.cholesterol = round_cholesterol(n.cholesterol)
    n.sodium = round_sp(n.sodium)
    n.total_carbohydrate = round_tdt(n.total_carbohydrate)
    n.dietary_fiber = round_tdt(n.dietary_fiber)
    n.total_sugars = round_tdt(n.total_sugars)
    n.protein = round_protein(n.protein)
    n.vitamin_d = round_vm(n.vitamin_d)
    n.vitamin_a = round_vm(n.vitamin_a)
    n.vitamin_c = round_vm(n.vitamin_c)
    n.calcium = round_vm(n.calcium)
    n.iron = round_vm(n.iron)
    n.potassium = round_vm(n.potassium)
    return n


def read_nutrition_facts(raw):
    nutrition = Nutrition(
        serving_size=raw.pop('Serving Size', None),
    )
    for key in raw:
        snaked_key = key.lower().replace(' ', '_')
        setattr(nutrition, snaked_key, raw[key]['amount'])
        setattr(nutrition, snaked_key + '_pdv', raw[key].get('percent_daily_value'))
    nutrition = standardize_nutrition(nutrition)
    return nutrition


def has_active_meal(hall):
    now = datetime.datetime.now(TIMEZONE)
    date = now.strftime(DATE_FMT)
    # TODO: we don't always want to use this default... but for now it's fine
    hall_id = app.config['FALLBACK_HALL_ID'] or hall.id
    meals = Meal.query.filter_by(hall_id=hall_id,
                                 date=date).all()
    time = now.strftime(TIME_FMT)
    for meal in meals:
        if meal.start_time < time < meal.end_time:
            return True
    return False


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
    for raw in data:
        if raw['TYPE'] != 'Residential':
            continue
        # We currently don't use this ID as it is relatively meaningless and using the building code is clearer
        #hall_id = int(raw['ID_LOCATION'])
        name = raw['DININGLOCATIONNAME']
        hall_id = HALL_IDS[name]
        hall = Hall.query.get(hall_id)
        if hall is None:
            hall = Hall(id=hall_id)
        # TODO: I can't figure out what this is for, so just omit it for now.
        #hall.code = int(raw['LOCATIONCODE']),
        # Get custom name override, falling back to provided name where applicable
        hall.name = FASTTRACK_NAME_OVERRIDES.get(name, name)
        hall.nickname = NICKNAMES.get(hall.name, hall.name)
        hall.occupancy = raw['CAPACITY']
        hall.open = not bool(raw['ISCLOSED'])
        # Override missing status information from API
        if not hall.open:
            hall.open = has_active_meal(hall)
            if hall.open:
                hall.occupancy = randint(0, 3)
        hall.address = raw['ADDRESS']
        hall.phone = raw['PHONE']
        # Ignore manager fields as they're now outdated.
        print('Parsing ' + hall.name)
        geolocation = raw.get('GEOLOCATION')
        if geolocation is not None:
            hall.latitude, hall.longitude = [float(coordinate) for coordinate in geolocation.split(',')]
        db.session.add(hall)
    db.session.commit()
    print('Done reading FastTrack data.')


def scrape_managers():
    print('Scraping managers.')
    ROOT = 'https://hospitality.yale.edu/residential-dining/'
    halls = Hall.query.all()
    HEADER_RE = re.compile(r'Management Team')
    Manager.query.delete()
    for hall in halls:
        slug = hall.name.lower().replace(' ', '-')
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
            manager = Manager()
            if len(contents) == 1:
                # The name is not a link, so no email is available
                manager.name, manager.position = contents[0].split(', ')
            elif len(contents) == 2:
                manager.name = contents[0].text
                manager.email = contents[0]['href'].replace('mailto:', '')
                manager.position = contents[1].lstrip(', ').replace('/ ', '/').replace(' /', '/')
            db.session.add(manager)
            manager.hall = hall
            print('Name: ' + manager.name)
            print('Email: %s' % manager.email)
            print('Position: %s' % manager.position)
    db.session.commit()


####################################
# JAMIX Selenium Web Parsing Section

###################################
# Functions for getting UI elements


def get_header_text():
    return driver.find_element_by_class_name('label-main-caption').text


def get_subheader_text():
    return driver.find_element_by_class_name('label-sub-caption').text


def get_tabs():
    driver.implicitly_wait(1)
    tabs_bar = driver.find_elements_by_class_name('v-tabsheet')
    driver.implicitly_wait(WAIT_PERIOD)
    if len(tabs_bar) == 0:
        return []
    return tabs_bar[0].find_elements_by_class_name('v-caption')


def get_courses():
    courses = driver.find_element_by_css_selector('div.v-verticallayout.v-layout.menu-sub-view').find_elements_by_class_name('v-button')
    return courses


def get_ingredients_and_nutrition_buttons():
    return driver.find_elements_by_css_selector('.v-button.v-widget.multiline.v-button-multiline.selection.v-button-selection.icon-align-right.v-button-icon-align-right.v-has-width')


def get_serving_size():
    text = driver.find_element_by_css_selector('.v-panel-content .v-panel-captionwrap').text.replace('Nutrition Facts\n', '')
    # Chop off parentheses
    if text[0] == '(' and text[-1] == ')':
        text = text[1:-1]
    return text


def get_item_nutrition_buttons():
    return driver.find_elements_by_css_selector('.v-button.nutrition')


def click_back():
    sleep()
    driver.find_element_by_css_selector('.button-navigation--previous .v-button').click()
    sleep()


def click_previous_date():
    previous_date_button = driver.find_element_by_class_name('button-date-selection--previous')
    previous_date_button.click()
    sleep()


def click_next_date():
    next_date_button = driver.find_element_by_class_name('button-date-selection--next')
    next_date_button.click()
    sleep()


def clean_hall_name(hall_name):
    hall_name = hall_name.replace(', Residential', '')
    if hall_name in JAMIX_HALL_NAMES:
        hall_name = JAMIX_HALL_NAMES[hall_name]
    return hall_name

######################
# Other util functions


def sleep():
    time.sleep(0.5)


def day_after(date):
    """
    Given a date, return the next day in that format.
    """
    fut = date + datetime.timedelta(days=1)
    return fut.strftime(DATE_FMT_JAMIX)


def seek_date(target_date) -> bool:
    """
    Seek toward a target date.
    :return: whether the date has been reached.
    """
    target_date = datetime.datetime.strptime(target_date, DATE_FMT_JAMIX)
    while True:
        current_date = get_subheader_text()
        current_date = datetime.datetime.strptime(current_date, DATE_FMT_JAMIX)
        if current_date == target_date:
            break
        if current_date < target_date:
            click_next_date()
        else:
            click_previous_date()
        sleep()


################################
# Scraping process functions


def seek_start(start_date=None):
    # Go to earliest available date or requested date
    while True:
        panels = driver.find_elements_by_class_name('v-panel-content')
        if len(panels) == 1:
            # The only panel is the no menus error message
            click_next_date()
            break
        click_previous_date()
        sleep()
        sleep()


def scrape_ingredients():
    """
    Scrape ingredients page onscreen.
    """
    sleep()
    ingredients = {}
    rows = driver.find_element_by_css_selector('.v-verticallayout.v-layout.v-vertical.v-widget.v-has-width.v-margin-top.v-margin-right.v-margin-bottom.v-margin-left .v-verticallayout').find_elements_by_xpath('./div[contains(@class, "v-slot")]')
    print('Found %d rows of ingredients data.' % len(rows))
    rows_processed = 0
    current_title = None
    looking_for = 'title'
    while rows_processed < len(rows):
        if looking_for == 'title':
            slots = rows[rows_processed].find_elements_by_css_selector('.v-label')
            current_title = slots[0].text
            ingredients[current_title] = {
                'diets': slots[1].text,
            }
            looking_for = 'ingredients'
            rows_processed += 1
        elif looking_for == 'ingredients':
            ingredients[current_title]['ingredients'] = rows[rows_processed].text
            looking_for = 'allergens'
            rows_processed += 1
        elif looking_for == 'allergens':
            text = rows[rows_processed].text
            if text.startswith('Allergens: '):
                ingredients[current_title]['allergens'] = text.replace('Allergens: ', '')
                rows_processed += 1
            looking_for = 'title'
    return ingredients


def scrape_nutrition():
    """
    Scrape a visible nutrition facts pane, whether for a full course or an individual item.
    """
    nutrition = {
        'Serving Size': get_serving_size(),
    }
    lists = driver.find_elements_by_css_selector('.v-panel-content ul')
    if len(lists) != 2:
        print('Warning: more than 2 uls found on nutrition page.')
    # The nutrition facts table is made with two uls, the first of which has the ingredient name and amount of it,
    # and the second of which has the daily values.
    # The elements in the left side list
    llist = BeautifulSoup(lists[0].get_attribute('innerHTML'), 'html.parser').findChildren(recursive=False)
    # The elements in the right side list
    rlist = BeautifulSoup(lists[1].get_attribute('innerHTML'), 'html.parser').findChildren(recursive=False)
    for lside, rside in zip(llist, rlist):
        # Skip if we're on an empty row
        if lside.text.strip() == '':
            continue
        spans = lside.find_all('span')
        ingredient = spans[0].text.lstrip('- ')
        amount = spans[1].text
        if ingredient == 'Calories':
            amount = float(amount.replace(',', '').replace(' kcal', ''))
        nutrition[ingredient] = {
            'amount': amount,
        }

        rtext = rside.text.strip(' %')
        if rtext:
            nutrition[ingredient]['percent_daily_value'] = int(rtext)
    return nutrition


def scrape_course_nutrition():
    """
    Scrape nutrition facts for each item in a course, starting from course nutrition page.
    """
    course_nutrition = {
        # The website offers nutrition facts for an entire course, but we ignore this.
        #'course': scrape_nutrition(),
        'items': {},
    }
    items = get_item_nutrition_buttons()
    if items:
        items_processed = 0
        while items_processed < len(items):
            # TODO: stop this from running twice on the first go. And same with other such constructs in this file.
            items = get_item_nutrition_buttons()
            item_name = items[items_processed].text
            print(f'Reading nutrition facts for {item_name}.')
            items[items_processed].click()
            sleep()

            course_nutrition['items'][item_name] = scrape_nutrition()

            click_back()

            items_processed += 1
    return course_nutrition


def scrape_course():
    """
    Scrape course that has been opened on the screen (i.e. Ingredients and Nutrition Facts buttons are showing).
    """
    course_name = get_header_text()
    course_name = COURSE_NAME_OVERRIDES.get(course_name, course_name)
    print(f'Parsing course {course_name}.')
    course = {
        'name': course_name,
    }
    # Grab and parse Ingredients page
    in_buttons = get_ingredients_and_nutrition_buttons()
    in_buttons[0].click()
    sleep()

    course['ingredients'] = scrape_ingredients()

    click_back()
    # Do again to reattach to the list
    in_buttons = get_ingredients_and_nutrition_buttons()
    in_buttons[1].click()
    sleep()

    course['nutrition'] = scrape_course_nutrition()

    click_back()  # to Ingredients/Nutrition Facts Selection pane
    sleep()
    return course


def scrape_meal(name):
    """
    Scrape the meal currently on the screen.
    """
    meal = {
        'name': name,
        'courses': [],
    }
    courses = get_courses()
    print('Found %d courses in this meal.' % len(courses))
    courses_processed = 0
    while courses_processed < len(courses):
        # Old references will be stale, so we must regenerate element list
        courses = get_courses()
        courses[courses_processed].click()
        sleep()

        meal['courses'].append(scrape_course())

        click_back()  # to main page/meal
        sleep()
        courses_processed += 1
    return meal


if os.path.exists(MENU_FILE):
    with open(MENU_FILE, 'r') as f:
        menus = json.load(f)
else:
    menus = {}


def scrape_right(hall_name):
    print('Parsing ' + hall_name)

    # Cycle through dates, collecting data
    while True:
        today_menu = {
            'date': get_subheader_text(),
            'meals': [],
        }

        print('Parsing date %s...' % today_menu['date'])

        panels = driver.find_elements_by_class_name('v-panel-content')
        if len(panels) == 1:
            break
        sleep()
        tabs = get_tabs()
        has_tabs = (len(tabs) >= MIN_MEALS_ALLOWED)
        if has_tabs:
            print('Found %d tabs on this page.' % len(tabs))
            tabs_processed = 0
            while tabs_processed < len(tabs):
                # TODO: remove repetition
                tabs = get_tabs()
                sleep()
                tabs[tabs_processed].click()
                sleep()
                meal_name = tabs[tabs_processed].text
                meal_name = MEAL_NAME_OVERRIDES.get(meal_name, meal_name)
                print(f'Checking tab {meal_name}.')

                today_menu['meals'].append(scrape_meal(meal_name))

                tabs_processed += 1
        else:
            print('Not enough tabs are available. Skipping date.')
            break

        menus[hall_name].append(today_menu)
        with open(MENU_FILE, 'w') as f:
            json.dump(menus, f)
        # Uncomment to work around the removed buttons issue, but makes everything less efficient.
        #driver.refresh()
        #seek_date(today_menu['date'])
        click_next_date()
        sleep()

    return True


def get_last_day(hall_name):
    # Handle multi-hall names
    # TODO this is messy
    # .split(' and ')[0].split(' & ')[0]
    if hall_name == 'ESM':
        hall_name = 'Ezra Stiles'
    hall_name = hall_name.split('/')[0].split(' & ')[0].split(' and ')[0]
    hall_name = clean_hall_name(hall_name)
    print(hall_name)
    hall = Hall.query.filter_by(name=hall_name).first()
    print(hall)
    last_meal = Meal.query.filter_by(hall_id=hall.id).order_by(Meal.date.desc()).first()
    last_day = last_meal.date if last_meal else None
    if hall_name in menus and menus[hall_name]:
        last_cached_day = datetime.datetime.strptime(menus[hall_name][-1]['date'], DATE_FMT_JAMIX).date()
        # Make lexicographic comparison
        if last_day is None or last_cached_day > last_day:
            last_day = last_cached_day
    return last_day


def parse(hall_jamix_id):
    finished = False
    stats = {
        'restarts': 0,
    }
    while not finished:
        driver.get('https://usa.jamix.cloud/menu/app?anro=97939&k=%d' % hall_jamix_id)
        sleep()
        hall_name = get_header_text()
        hall_name = clean_hall_name(hall_name)
        if hall_name not in menus:
            menus[hall_name] = []
        # If there's already some days in the list, then go to the next day.
        # Otherwise, go all the way to the start.
        # TODO: in theory, if we didn't run the scraper for a really long time, this could take us
        # back to a time where there's no data, and the parser will think it's finished with this hall.
        # Hopefully we'll run often enough that this won't happen, but it would be good to be sure.
        last_day = get_last_day(hall_name)
        if last_day:
            seek_date(day_after(last_day))
        else:
            # Uncomment to jump ahead by a few days if we need to look at a future time
            #seek_date(
            #    (datetime.date.today() + datetime.timedelta(days=5)).strftime(DATE_FMT_JAMIX)
            #)
            seek_start()

        try:
            finished = scrape_right(hall_name)
        except (ElementClickInterceptedException, ElementNotInteractableException, IndexError) as e:
            print('Squashing error...')
            print(e)
            stats['restarts'] += 1
    return hall_name, menus[hall_name], stats


def get_last_covered_day(hall):
    last_meal = Meal.query.filter_by(hall_id=hall.id).order_by(Meal.date.desc()).first()
    if last_meal is None:
        return None
    return last_meal.date


def parse_hall(hall_name):
    print('Parsing hall ' + hall_name)
    hall = Hall.query.filter_by(name=hall_name).first()
    stats = {
        'found': {
            'days': 0,
            'meals': 0,
            'items': 0,
        },
        'inserted': {
            'meals': 0,
            'items': 0,
        },
        'end_day': None,
        'days_left': None,
    }
    for day_d in menus[hall_name]:
        stats['found']['days'] += 1
        date = datetime.datetime.strptime(day_d['date'], DATE_FMT_JAMIX).date()
        print('Parsing day ' + day_d['date'])
        # TODO: some days may actually have less than three meals.
        if len(day_d['meals']) < MIN_MEALS_ALLOWED:
            print('Not enough meals found, skipping day.')
            continue
        for meal_d in day_d['meals']:
            stats['found']['meals'] += 1
            meal_name = meal_d['name']
            existing_meal = Meal.query.filter_by(hall_id=hall.id, name=meal_name, date=date).first()
            if existing_meal is not None:
                print('Meal already exists.')
                continue
            print('Parsing meal ' + meal_name)
            if meal_name == 'Breakfast':
                start_time = '08:00'
                end_time = '10:30'
            elif meal_name == 'Lunch':
                start_time = '11:30'
                end_time = '14:00'
            elif 'Dinner' in meal_name:
                start_time = '17:00'
                end_time = '19:30'
            else:
                start_time = None
                end_time = None
            meal = Meal(
                name=meal_name,
                date=date,
                start_time=start_time,
                end_time=end_time,
            )
            meal.hall = hall
            stats['inserted']['meals'] += 1
            for course_d in meal_d['courses']:
                course_name = course_d['name']
                print('Parsing course ' + course_name)
                # Note that both ingredients and nutrition_d['items'] are dictionaries,
                # with the keys being the names of the items.
                ingredients = course_d['ingredients']
                nutrition_d = course_d['nutrition']
                for item_name in ingredients:
                    stats['found']['items'] += 1
                    print('Parsing item ' + item_name)
                    clean_item_name = ITEM_NAME_OVERRIDES.get(item_name, item_name).replace('`', '\'')
                    item = Item(
                        name=clean_item_name,
                        ingredients=ingredients[item_name]['ingredients'],
                        course=course_name,

                        # Set to default for later operations
                        # Database will put in the default values, but we need
                        # to compare them for deduplication below.
                        alcohol=False,
                        shellfish=False,
                        tree_nut=False,
                        peanuts=False,
                        dairy=False,
                        egg=False,
                        pork=False,
                        fish=False,
                        soy=False,
                        wheat=False,
                        gluten=False,
                        coconut=False,

                        nuts=False,
                    )
                    diets = ingredients[item_name]['diets'].split(', ')
                    item.animal_products = not ('VG' in diets)
                    item.meat = not ('V' in diets)
                    item.gluten = not ('GF' in diets)
                    allergens = ingredients[item_name].get('allergens')
                    if allergens:
                        allergens = allergens.split(', ')
                        for allergen in allergens:
                            setattr(item, allergen.lower(), True)

                    # TODO: DRY
                    existing_item = Item.query.filter_by(
                        name=item.name,
                        ingredients=item.ingredients,
                        course=item.course,
                        meat=item.meat,
                        animal_products=item.animal_products,
                        alcohol=item.alcohol,
                        shellfish=item.shellfish,
                        tree_nut=item.tree_nut,
                        peanuts=item.peanuts,
                        dairy=item.dairy,
                        egg=item.egg,
                        pork=item.pork,
                        fish=item.fish,
                        soy=item.soy,
                        wheat=item.wheat,
                        gluten=item.gluten,
                        coconut=item.coconut,
                    ).first()
                    if existing_item is None:
                        # Fix missing tree nut allergens
                        existing_item = Item.query.filter_by(
                            name=item.name,
                            ingredients=item.ingredients,
                            course=item.course,
                            meat=item.meat,
                            animal_products=item.animal_products,
                            alcohol=item.alcohol,
                            shellfish=item.shellfish,
                            tree_nut=not item.tree_nut,
                            peanuts=item.peanuts,
                            dairy=item.dairy,
                            egg=item.egg,
                            pork=item.pork,
                            fish=item.fish,
                            soy=item.soy,
                            wheat=item.wheat,
                            gluten=item.gluten,
                            coconut=item.coconut,
                        ).first()
                        if existing_item is not None:
                            existing_item.tree_nut = item.tree_nut
                    print(existing_item)
                    if existing_item is not None:
                        item = existing_item
                    else:
                        stats['inserted']['items'] += 1
                        db.session.add(item)
                        if nutrition_d['items'].get(item_name):
                            # Read nutrition facts
                            # TODO: 'nutrition' or 'nutrition facts'?
                            nutrition = read_nutrition_facts(nutrition_d['items'][item_name])
                            db.session.add(nutrition)
                            item.nutrition = nutrition
                    item.meals.append(meal)
                    # TODO: this should always be present, but handle its absence in case the scraper broke
            db.session.add(meal)
    db.session.commit()
    stats['end_day'] = get_last_covered_day(hall)
    return stats


def scrape_jamix():
    print('Reading JAMIX menu data.')
    create_driver()
    stats = {
        'start_time': datetime.datetime.now(),
        'end_time': None,
        'halls': {},
    }

    # Iterate through halls
    for hall_jamix_id in range(1, 11 + 1):
        hall_name, hall, scrape_stats = parse(hall_jamix_id)
        # Separate multi-hall menus
        # TODO: should we do this at request time?
        if '/' in hall_name or ' & ' in hall_name or ' and ' in hall_name:
            value = menus.pop(hall_name)
            # TODO: just use regex
            if '/' in hall_name:
                hall_name_a, hall_name_b = hall_name.split('/')
            elif ' & ' in hall_name:
                hall_name_a, hall_name_b = hall_name.split(' & ')
            elif ' and ' in hall_name:
                hall_name_a, hall_name_b = hall_name.split(' and ')
            hall_name_a = clean_hall_name(hall_name_a)
            hall_name_b = clean_hall_name(hall_name_b)
            menus[hall_name_a] = value
            menus[hall_name_b] = value
            stats['halls'][hall_name_a] = {
                **scrape_stats,
                **parse_hall(hall_name_a),
            }
            stats['halls'][hall_name_b] = {
                **scrape_stats,
                **parse_hall(hall_name_b),
            }
        else:
            stats['halls'][hall_name] = {
                **scrape_stats,
                **parse_hall(hall_name),
            }

    now = datetime.datetime.now()
    for hall_name in stats['halls']:
        stats['halls'][hall_name]['days_left'] = (stats['halls'][hall_name]['end_day'] - now.date()).days + 1
    stats['end_time'] = now
    db.session.commit()
    print('Done.')
    return stats


@celery.task
def scrape(fasttrack_only=False):
    scrape_fasttrack()
    if not fasttrack_only:
        scrape_managers()
        stats = scrape_jamix()
        send_scraper_report(stats)
        print(stats)


@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(60 * 5, scrape.s(fasttrack_only=True), name='FastTrack scrape')
    sender.add_periodic_task(
        crontab(hour=0, minute=0),
        scrape.s(fasttrack_only=False),
        name='Full scrape'
    )
