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

def get_header():
    return driver.find_element_by_class_name('label-main-caption').text

def get_courses():
    return driver.find_element_by_css_selector('div.v-verticallayout.v-layout.v-vertical.v-widget.animated.v-verticallayout-animated.fade-in-down.v-verticallayout-fade-in-down.v-has-width.v-margin-top.v-margin-bottom').find_elements_by_class_name('v-button')

def get_properties():
    return driver.find_elements_by_css_selector('.v-button.v-widget.multiline.v-button-multiline.selection.v-button-selection.icon-align-right.v-button-icon-align-right.v-has-width')

college = get_header()
print('Parsing ' + college)


# Go to earliest available date
while True:
    time.sleep(1)
    panels = driver.find_elements_by_class_name('v-panel-content')
    if len(panels) == 1:
        break
    previous_date_button = driver.find_element_by_class_name('button-date-selection--previous')
    previous_date_button.click()

# Cycle through dates, collecting data
while True:
    next_date_button = driver.find_element_by_class_name('button-date-selection--next')
    next_date_button.click()

    time.sleep(1)

    panels = driver.find_elements_by_class_name('v-panel-content')
    if len(panels) == 1:
        break
    tabs = driver.find_element_by_class_name('v-tabsheet').find_elements_by_class_name('v-caption')
    print('Found %d tabs on this page.' % len(tabs))
    tabs_processed = 0
    while tabs_processed < len(tabs):
        tabs[tabs_processed].click()
        meal_name = tabs[tabs_processed].text

        courses = get_courses()
        courses_processed = 0
        while courses_processed < len(courses):
            courses = get_courses()
            courses[courses_processed].click()

            properties = get_properties()
            properties[0].click()

            driver.find_element_by_css_selector('.v-verticallayout.v-layout.v-vertical.v-widget.v-has-width.v-margin-top.v-margin-right.v-margin-bottom.v-margin-left')[1].get_elements_by_xpath('//div[@class="')
            courses_processed += 1

        tabs_processed += 1
