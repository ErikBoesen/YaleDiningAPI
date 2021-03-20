from app import app, db


meals_x_items = db.Table(
    'meals_x_items',
    db.Column('meal_id', db.Integer, db.ForeignKey('meals.id'), nullable=False),
    db.Column('item_id', db.Integer, db.ForeignKey('items.id'), nullable=False),
)


class Hall(db.Model):
    __tablename__ = 'halls'
    __serializable__ = ('id', 'name', 'nickname', 'open', 'occupancy', 'latitude', 'longitude', 'address', 'phone')
    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String, nullable=False)
    nickname = db.Column(db.String, nullable=False)
    open = db.Column(db.Boolean, nullable=False)
    occupancy = db.Column(db.Integer, nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    address = db.Column(db.String, nullable=False)
    phone = db.Column(db.String, nullable=False)

    managers = db.relationship('Manager', cascade='all,delete', back_populates='hall')
    meals = db.relationship('Meal', cascade='all,delete', back_populates='hall')


class Manager(db.Model):
    __tablename__ = 'managers'
    __serializable__ = ('id', 'name', 'email', 'position', 'hall_id')
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, nullable=False)
    email = db.Column(db.String)
    position = db.Column(db.String)

    hall_id = db.Column(db.String, db.ForeignKey('halls.id'))
    hall = db.relationship('Hall', back_populates='managers')


class Meal(db.Model):
    __tablename__ = 'meals'
    __serializable__ = ('id', 'name', 'date', 'start_time', 'end_time', 'hall_id')
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.String)
    end_time = db.Column(db.String)

    hall_id = db.Column(db.String, db.ForeignKey('halls.id'))
    hall = db.relationship('Hall', back_populates='meals')

    items = db.relationship(
        'Item', secondary=meals_x_items, lazy='subquery',
        backref=db.backref('meals', lazy=True))

    def search(hall_id, date=None, start_date=None, end_date=None):
        meals = Meal.query.filter_by(hall_id=hall_id)
        if date is not None:
            meals = meals.filter(Meal.date == date)
        else:
            if start_date is None:
                start_date = datetime.date.today()
            else:
                start_date = datetime.datetime.strptime(start_date, DATE_FMT)
            meals = meals.filter(start_date <= Meal.date)
            if end_date is not None:
                meals = meals.filter(Meal.date <= end_date)
        meals = meals.order_by(Meal.date, Meal.start_time)
        meals = meals.all()
        return meals


class Item(db.Model):
    __tablename__ = 'items'
    __serializable__ = (
        'id', 'name', 'ingredients', 'course',
        'meat', 'animal_products', 'alcohol', 'tree_nut', 'shellfish', 'peanuts', 'dairy', 'egg', 'pork', 'fish', 'soy', 'wheat', 'gluten', 'coconut',
        'meal_id', 'nuts',
    )
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, nullable=False)
    ingredients = db.Column(db.String)
    course = db.Column(db.String)

    meat = db.Column(db.Boolean, default=False)
    animal_products = db.Column(db.Boolean, default=False)
    alcohol = db.Column(db.Boolean, default=False)
    tree_nut = db.Column(db.Boolean, default=False)
    shellfish = db.Column(db.Boolean, default=False)
    peanuts = db.Column(db.Boolean, default=False)
    dairy = db.Column(db.Boolean, default=False)
    egg = db.Column(db.Boolean, default=False)
    pork = db.Column(db.Boolean, default=False)
    fish = db.Column(db.Boolean, default=False)
    soy = db.Column(db.Boolean, default=False)
    wheat = db.Column(db.Boolean, default=False)
    gluten = db.Column(db.Boolean, default=False)
    coconut = db.Column(db.Boolean, default=False)

    meal_id = db.Column(db.Integer, default=0)
    # Obsolete
    nuts = db.Column(db.Boolean, default=False)

    nutrition = db.relationship('Nutrition', cascade='all,delete,delete-orphan', uselist=False, back_populates='item')


class Nutrition(db.Model):
    __tablename__ = 'nutrition'
    __serializable__ = (
        'serving_size', 'calories',
        'total_fat', 'saturated_fat', 'trans_fat', 'cholesterol', 'sodium', 'total_carbohydrate', 'dietary_fiber', 'total_sugars', 'protein',
        'vitamin_d', 'vitamin_a', 'vitamin_c', 'calcium', 'iron', 'potassium',
        'total_fat_pdv', 'saturated_fat_pdv', 'trans_fat_pdv', 'cholesterol_pdv', 'sodium_pdv', 'total_carbohydrate_pdv', 'dietary_fiber_pdv', 'total_sugars_pdv', 'protein_pdv',
        'vitamin_d_pdv', 'vitamin_a_pdv', 'vitamin_c_pdv', 'calcium_pdv', 'iron_pdv', 'potassium_pdv',
        'item_id',
    )
    serving_size = db.Column(db.String)
    calories = db.Column(db.Integer)

    total_fat = db.Column(db.String)
    saturated_fat = db.Column(db.String)
    trans_fat = db.Column(db.String)
    cholesterol = db.Column(db.String)
    sodium = db.Column(db.String)
    total_carbohydrate = db.Column(db.String)
    dietary_fiber = db.Column(db.String)
    total_sugars = db.Column(db.String)
    protein = db.Column(db.String)
    vitamin_d = db.Column(db.String)
    vitamin_a = db.Column(db.String)
    vitamin_c = db.Column(db.String)
    calcium = db.Column(db.String)
    iron = db.Column(db.String)
    potassium = db.Column(db.String)

    # Percent Daily Value
    total_fat_pdv = db.Column(db.Integer)
    saturated_fat_pdv = db.Column(db.Integer)
    trans_fat_pdv = db.Column(db.Integer)
    cholesterol_pdv = db.Column(db.Integer)
    sodium_pdv = db.Column(db.Integer)
    total_carbohydrate_pdv = db.Column(db.Integer)
    dietary_fiber_pdv = db.Column(db.Integer)
    total_sugars_pdv = db.Column(db.Integer)
    protein_pdv = db.Column(db.Integer)
    vitamin_d_pdv = db.Column(db.Integer)
    vitamin_a_pdv = db.Column(db.Integer)
    vitamin_c_pdv = db.Column(db.Integer)
    calcium_pdv = db.Column(db.Integer)
    iron_pdv = db.Column(db.Integer)
    potassium_pdv = db.Column(db.Integer)

    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), primary_key=True)
    item = db.relationship('Item', back_populates='nutrition')
