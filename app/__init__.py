from flask import Flask
from config import Config
from celery import Celery
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate


app = Flask(__name__)
app.config.from_object(Config)
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)
cors = CORS(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db)

from app import routes, models, errors, api, util
app.register_blueprint(api.api_bp, url_prefix='/api')
