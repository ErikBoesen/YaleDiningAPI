from flask import Blueprint, request

from app import db
from app.models import Location, Manager, Meal, Course, Item, Nutrition
from app.util import to_json

import datetime


DATE_FMT = '%Y-%m-%d'

api_bp = Blueprint('api', __name__)


@api_bp.route('/locations')
def api_locations():
    locations = Location.query.all()
    return to_json(locations)


@api_bp.route('/locations/<location_id>')
def api_location(location_id):
    location = Location.query.get_or_404(location_id)
    return to_json(location)


@api_bp.route('/locations/<location_id>/meals')
def api_location_meals(location_id):
    meals = Meal.query.filter_by(location_id=location_id)
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
    meal = Meal.query.get(meal_id)
    return to_json(meal)


@api_bp.route('/meals/<meal_id>/items')
def api_meal_items(meal_id):
    items = Item.query.filter_by(meal_id=meal_id).all()
    return to_json(items)
