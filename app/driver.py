import requests
import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions

WAIT_PERIOD = 10

driver = webdriver.Firefox()
driver.get('https://usa.jamix.cloud/menu/app?anro=97939&k=1')
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

def get_item_nutrition_buttons():
    return driver.find_elements_by_css_selector('.v-button.nutrition')

def click_back():
    sleep()
    driver.find_element_by_css_selector('.button-navigation--previous .v-button').click()
    sleep()

######################
# Other util functions

def sleep():
    time.sleep(0.8)

################################
# Parsing process functions

def scan_to_start():
    # Go to earliest available date or requested date
    while True:
        panels = driver.find_elements_by_class_name('v-panel-content')
        if len(panels) == 1:
            # The only panel is the no menus error message
            break
        previous_date_button = driver.find_element_by_class_name('button-date-selection--previous')
        previous_date_button.click()
        sleep()


def parse_ingredients():
    """
    Parse ingredients page that's on the screen.
    """
    ingredients = {}
    rows = driver.find_elements_by_css_selector('.v-panel-content.v-scrollable')[-1].find_elements_by_xpath('//div[@class="v-slot"]')
    print('Found %d rows of ingredients data.' % len(rows))
    rows_processed = 0
    current_title = None
    looking_for = 'title'
    while rows_processed < len(rows):
        if looking_for == 'title':
            current_title = rows[rows_processed].text
            ingredients[current_title] = {}
            looking_for = 'ingredients'
            rows_processed += 1
        elif looking_for == 'ingredients':
            ingredients[current_title]['ingredients'] = rows[rows_processed].text
            looking_for = 'allergens'
            rows_processed += 1
        elif looking_for == 'allergens':
            text = rows[rows_processed].text
            if text.startswith('Allergens'):
                ingredients[current_title]['allergens'] = text
                rows_processed += 1
            looking_for = 'title'
    return

def parse_nutrition_facts():
    """
    Parse nutrition facts for a course.
    """
    # TODO: parse nutrition facts page too
    items = get_item_nutrition_buttons()
    if items:
        items_processed = 0
        while items_processed < len(items):
            # TODO: stop this from running twice on the first go. And same with other such constructs in this file.
            items = get_item_nutrition_buttons()
            items[items_processed].click()
            sleep()

            # TODO: parse these pages too
            click_back()

            items_processed += 1


def parse_course():
    """
    Parse course that has been opened on the screen (i.e. Ingredients and Nutrition Facts buttons are showing).
    """
    course = {
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


def parse_right():
    # Cycle through dates, collecting data
    menus = []
    while True:
        next_date_button = driver.find_element_by_class_name('button-date-selection--next')
        next_date_button.click()
        sleep()

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
    print(menus)


college = get_header_text()
print('Parsing ' + college)
scan_to_start()
parse_right()
