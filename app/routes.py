from flask import render_template, request, jsonify, g
from app import app, db, scraper
#from app.models import


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/scraper', methods=['GET', 'POST'])
def scrape():
    if request.method == 'GET':
        return render_template('scraper.html')
    payload = request.get_json()
    print('Kicking off scraper.')
    scraper.scrape.apply_async()
    return '', 200
