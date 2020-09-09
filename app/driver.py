import requests
import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions

driver = webdriver.Firefox()
driver.get('https://usa.jamix.cloud/menu/app?anro=97939&k=1')
driver.implicitly_wait(10)

###################################
# Functions for getting UI elements

def get_header_text():
    return driver.find_element_by_class_name('label-main-caption').text

def get_subheader_text():
    return driver.find_element_by_class_name('label-sub-caption').text

def get_tabs():
    tabs_bar = driver.find_elements_by_class_name('v-tabsheet')
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

def parse_meal():
    """
    Parse the meal currently on the screen, whether or not it was accessed via a tab.
    """
    courses = get_courses()
    courses_processed = 0
    while courses_processed < len(courses):
        courses = get_courses()
        courses[courses_processed].click()
        sleep()

        # Grab and parse Ingredients page
        in_buttons = get_ingredients_and_nutrition_buttons()
        in_buttons[0].click()
        sleep()
        rows = driver.find_elements_by_css_selector('.v-panel-content.v-scrollable')[-1].find_elements_by_xpath('//div[@class="v-slot"]')
        rows_processed = 0
        print('Found %d rows.' % len(rows))
        # TODO: process page.

        click_back()
        # Do again to reattach to the list
        in_buttons = get_ingredients_and_nutrition_buttons()
        in_buttons[1].click()
        sleep()
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
        click_back()  # to Ingredients/Nutrition Facts Selection pane
        sleep()
        click_back()  # to main page/meal
        sleep()
        courses_processed += 1


def parse_right():
    # Cycle through dates, collecting data
    while True:
        sleep()
        next_date_button = driver.find_element_by_class_name('button-date-selection--next')
        next_date_button.click()

        sleep()

        date = driver.find_element_by_css_selector('.v-label.v-widget.sub-title.v-label-sub-title.v-has-width').text
        print('Parsing date %s...' % date)

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

                parse_meal()

                tabs_processed += 1
        else:
            print('No tabs are available.')
            parse_meal()


college = get_header_text()
print('Parsing ' + college)
scan_to_start()
parse_right()
