from flask import Blueprint, request

from app import app, db
from app.models import Hall, Manager, Meal, Item, Nutrition
from app.util import to_json

import os
import datetime


api_bp = Blueprint('api', __name__)

STATUS = to_json({
    'message': os.environ.get('STATUS_MESSAGE'),
    'min_version_ios': int(os.environ.get('STATUS_MIN_VERSION_IOS', 0)),
    'min_version_android': int(os.environ.get('STATUS_MIN_VERSION_ANDROID', 0)),
    # Deprecated, still used by older versions on iOS
    'min_version': 0,
})


@api_bp.route('/status')
def api_status():
    return STATUS


@api_bp.route('/halls')
def api_halls():
    halls = Hall.query.order_by(Hall.nickname).all()
    return to_json(halls)


@api_bp.route('/halls/<hall_id>')
def api_hall(hall_id):
    hall = Hall.query.get_or_404(hall_id)
    return to_json(hall)


@api_bp.route('/halls/<hall_id>/managers')
def api_hall_managers(hall_id):
    hall = Hall.query.get_or_404(hall_id)
    managers = hall.managers
    return to_json(managers)


@api_bp.route('/halls/<hall_id>/meals')
def api_hall_meals(hall_id):
    hall = Hall.query.get_or_404(hall_id)

    date = request.args.get('date')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    meals = Meal.search(hall_id=hall_id,
                        date=date,
                        start_date=start_date,
                        end_date=end_date)

    if not meals:
        fallback_hall_id = app.config['FALLBACK_HALL_ID']
        if fallback_hall_id:
            meals = Meal.search(fallback_hall_id,
                                date=date,
                                start_date=start_date,
                                end_date=end_date)

    return to_json(meals)


@api_bp.route('/managers')
def api_managers():
    managers = Manager.query.all()
    return to_json(managers)


@api_bp.route('/meals')
def api_meals():
    date = request.args.get('date')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    meals = Meal.search(date=date,
                        start_date=start_date,
                        end_date=end_date)
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


@api_bp.route('/items')
def api_items():
    items = Item.query.all()
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
