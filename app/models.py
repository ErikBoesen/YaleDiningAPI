from app import app, db


class Location:
    __tablename__ = 'locations'
    id = db.Column(db.Integer, primary=True)
    code = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String, nullable=False)
    type = db.Column(db.String, nullable=False)
    capacity = db.Column(db.Integer)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    is_open = db.Column(db.Boolean, nullable=False)
    address = db.Column(db.String, nullable=False)
    phone = db.Column(db.String)

    managers = db.relationship('Manager', backref='location')

class Manager:
    __tablename__ = 'managers'
    id = db.Column(db.Integer, primary=True, autoincrement=True)
    name = db.Column(db.String)
    email = db.Column(db.String)

    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'))
