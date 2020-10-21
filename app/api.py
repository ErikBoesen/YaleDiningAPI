from flask import Blueprint, request

from app import db
from app.models import Location, Manager, Meal, Course, Item, Nutrition
from app.util import to_json

import datetime


DATE_FMT = '%Y-%m-%d'

api_bp = Blueprint('api', __name__)


@api_bp.route('/locations')
def api_locations():
    locations = Location.query.filter_by(type='Residential').all()
    return to_json(locations)


@api_bp.route('/locations/<location_id>')
def api_location(location_id):
    location = Location.query.get_or_404(location_id)
    return to_json(location)


@api_bp.route('/locations/<location_id>/managers')
def api_managers(location_id):
    location = Location.query.get_or_404(location_id)
    managers = location.managers
    return to_json(managers)


@api_bp.route('/locations/<location_id>/meals')
def api_location_meals(location_id):
    # TODO: use this later on, right now it's mostly a 404 check
    location = Location.query.get_or_404(location_id)
    meals = Meal.query.filter_by(location_id=location_id)
    date = request.args.get('date')
    if date is not None:
        meals = meals.filter(Meal.date == date)
    else:
        start_date = request.args.get('start_date')
        if start_date is None:
            start_date = datetime.date.today()
        else:
            start_date = datetime.datetime.strptime(start_date, DATE_FMT)
        meals = meals.filter(start_date <= Meal.date)
        end_date = request.args.get('end_date')
        if end_date is not None:
            meals = meals.filter(Meal.date <= end_date)
    meals = meals.all()
    return to_json(meals)


@api_bp.route('/meals/<meal_id>')
def api_meal(meal_id):
    meal = Meal.query.get_or_404(meal_id)
    return to_json(meal)


@api_bp.route('/meals/<meal_id>/items')
def api_meal_items(meal_id):
    meal = Meal.query.get_or_404(meal_id)
    items = meal.items
    return to_json(items)


@api_bp.route('/meals/<meal_id>/courses')
def api_meal_courses(meal_id):
    meal = Meal.query.get_or_404(meal_id)
    courses = meal.courses
    return to_json(courses)


@api_bp.route('/courses/<course_id>')
def api_course(course_id):
    course = Course.query.get_or_404(course_id)
    return to_json(course)


@api_bp.route('/courses/<course_id>/items')
def api_course_items(course_id):
    course = Course.query.get_or_404(course_id)
    items = course.items
    return to_json(items)


@api_bp.route('/items/<item_id>')
def api_item(item_id):
    item = Item.query.get_or_404(item_id)
    return to_json(item)


@api_bp.route('/items/<item_id>/nutrition')
def api_item_nutrition(item_id):
    item = Item.query.get_or_404(item_id)
    nutrition = item.nutrition
    return to_json(nutrition)
