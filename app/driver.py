import requests
import time
import json
import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions

WAIT_PERIOD = 10

driver = webdriver.Firefox()
driver.implicitly_wait(WAIT_PERIOD)

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
    print('Found %d courses this time.' % len(courses))
    return courses

def get_ingredients_and_nutrition_buttons():
    return driver.find_elements_by_css_selector('.v-button.v-widget.multiline.v-button-multiline.selection.v-button-selection.icon-align-right.v-button-icon-align-right.v-has-width')

def get_portion_size():
    text = driver.find_element_by_css_selector('.v-panel-content .v-panel-captionwrap').text.replace('Nutrition Facts\n', '')
    # Chop off parentheses
    if text.startswith('(') and text.endswith(')'):
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

######################
# Other util functions

def sleep():
    time.sleep(0.8)

def day_after(date):
    """
    Given a date, return the next day in that format.
    """
    fmt = '%A, %B %d, %Y'
    cur = datetime.datetime.strptime(date, fmt)
    fut = cur + datetime.timedelta(days=1)
    return fut.strftime(fmt)

def seek_date(current_date, target_date) -> bool:
    """
    Seek toward a target date.
    :return: whether the date has been reached.
    """
    # TODO this name is kinda unclear
    fmt = '%A, %B %d, %Y'
    current_date = datetime.datetime.strptime(current_date, fmt)
    target_date = datetime.datetime.strptime(target_date, fmt)
    if current_date == target_date:
        return True
    if current_date < target_date:
        click_next_date()
    else:
        click_previous_date()
    sleep()
    return False

################################
# Parsing process functions

def scan_to_start(start_date=None):
    # Go to earliest available date or requested date
    if start_date:
        # TODO: deduplicate
        date = get_subheader_text()
        while seek_date(date, start_date):
            date = get_subheader_text()
    else:
        while True:
            panels = driver.find_elements_by_class_name('v-panel-content')
            if len(panels) == 1:
                # The only panel is the no menus error message
                click_next_date()
                break
            click_previous_date()
            sleep()


def parse_ingredients():
    """
    Parse ingredients page that's on the screen.
    """
    ingredients = {}
    rows = driver.find_element_by_css_selector('.v-verticallayout.v-layout.v-vertical.v-widget.v-has-width.v-margin-top.v-margin-right.v-margin-bottom.v-margin-left .v-verticallayout').find_elements_by_xpath('./div[contains(@class, "v-slot")]')
    print('Found %d rows of ingredients data.' % len(rows))
    rows_processed = 0
    current_title = None
    looking_for = 'title'
    while rows_processed < len(rows):
        if looking_for == 'title':
            slots = rows[rows_processed].find_elements_by_css_selector('.v-label')
            print('------------------ROWS:------')
            print([row.text for row in rows])
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


def parse_nutrition_facts():
    """
    Parse a visible nutrition facts pane, whether for a full course or an individual item.
    """
    nutrition_facts = {
        'Portion Size': get_portion_size,
    }
    lists = driver.find_elements_by_css_selector('.v-panel-content ul')
    if len(lists) != 2:
        print('Warning: more than 2 uls found on nutrition facts page.')
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
        nutrition_facts[ingredient] = {
            'amount': amount,
        }

        rtext = rside.text.strip(' %')
        if rtext:
            nutrition_facts[ingredient]['percent_daily_value'] = int(rtext)
    return nutrition_facts


def parse_nutrition_facts_course():
    """
    Parse nutrition facts for an entire course.
    """
    nutrition_facts = {
        'course': parse_nutrition_facts(),
        'items': {},
    }
    items = get_item_nutrition_buttons()
    if items:
        items_processed = 0
        while items_processed < len(items):
            # TODO: stop this from running twice on the first go. And same with other such constructs in this file.
            items = get_item_nutrition_buttons()
            item_name = items[items_processed].text
            items[items_processed].click()
            sleep()

            nutrition_facts['items'][item_name] = parse_nutrition_facts()

            click_back()

            items_processed += 1
    return nutrition_facts


def parse_course():
    """
    Parse course that has been opened on the screen (i.e. Ingredients and Nutrition Facts buttons are showing).
    """
    course = {
        'name': get_header_text(),
    }
    # Grab and parse Ingredients page
    in_buttons = get_ingredients_and_nutrition_buttons()
    in_buttons[0].click()
    sleep()

    course['ingredients'] = parse_ingredients()

    click_back()
    # Do again to reattach to the list
    in_buttons = get_ingredients_and_nutrition_buttons()
    in_buttons[1].click()
    sleep()

    course['nutrition_facts'] = parse_nutrition_facts_course()

    click_back()  # to Ingredients/Nutrition Facts Selection pane
    sleep()
    return course

def parse_meal(name):
    """
    Parse the meal currently on the screen, whether or not it was accessed via a tab.
    """
    meal = {
        'name': name,
        'courses': [],
    }
    courses = get_courses()
    courses_processed = 0
    while courses_processed < len(courses):
        courses = get_courses()
        courses[courses_processed].click()
        sleep()

        meal['courses'].append(parse_course())

        click_back()  # to main page/meal
        sleep()
        courses_processed += 1
    return meal

menus = []

def parse_right():
    college = get_header_text()
    print('Parsing ' + college)

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
        has_tabs = (len(tabs) > 0)
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

                today_menu['meals'].append(parse_meal(meal_name))

                tabs_processed += 1
        else:
            print('No tabs are available. Parsing single meal.')
            # TODO: does this default hold?
            today_menu['meals'].append(parse_meal('Breakfast'))

        menus.append(today_menu)
        print(json.dumps(menus))
        with open('menus.json', 'w') as f:
            json.dump(menus, f)
        click_next_date()
        sleep()

    return True

def parse(location_id):
    finished = False
    while not finished:
        driver.get('https://usa.jamix.cloud/menu/app?anro=97939&k=%d' % location_id)
        try:
            if len(menus):
                scan_to_start(start_date=day_after(menus[-1]['date']))
            else:
                scan_to_start()
            finished = parse_right()
        except Exception as e:
            print('Squashing error...')
            print(e)
    return menus

# Iterate through colleges
for location_id in range(12):
    parse(location_id)
