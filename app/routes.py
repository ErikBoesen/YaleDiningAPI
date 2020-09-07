from flask import render_template, request, jsonify, g
from app import app, db, tasks
#from app.models import


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/scraper', methods=['GET', 'POST'])
def scraper():
    if request.method == 'GET':
        return render_template('scraper.html')
    payload = request.get_json()
    tasks.scrape.apply_async()
    return '', 200
