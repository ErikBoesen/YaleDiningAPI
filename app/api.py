from flask import Blueprint
from app import db
from app.models import Location, Manager, Meal, Item, Nutrition
from app.util import to_json


api_bp = Blueprint('api', __name__)


@api_bp.route('/locations')
def api_locations():
    locations = Location.query.all()
    return to_json(locations)
