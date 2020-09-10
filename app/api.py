from flask import Blueprint, jsonify, request, g
from app import db
from app.util import ModelEncoder


api_bp = Blueprint('api', __name__)


@api_bp.route('/locations')
def api_locations():
    return jsonify({})
