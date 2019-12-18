import logging
import re
from datetime import datetime
from functools import wraps
import os

import requests
from bs4 import BeautifulSoup
from werkzeug.contrib.cache import SimpleCache

from flask import Flask, json, request

from utils.fetch import random_user_agent as _random_user_agent

logger = logging.getLogger('app')


__cwd__ = os.getcwd()
__location__ = os.path.realpath(
    os.path.join(__cwd__, os.path.dirname(__file__))
)

with open(os.path.join(__location__, 'utils', 'stations.json'), 'r') as fp:
    _STATIONS = json.load(fp)


app = Flask(__name__)

cache = SimpleCache()

def cached(timeout=5 * 60, key='view/%s'):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            cache_key = key % request.path
            rv = cache.get(cache_key)
            if rv is not None:
                return rv
            rv = f(*args, **kwargs)
            cache.set(cache_key, rv, timeout=timeout)
            return rv
        return decorated_function
    return decorator


def get_departures(station_id):
    """
    get_departures extracts the departure time at the station

    :param station_id: id of the station, e.g., 46 is Drehbrucke
    :type station_id: int
    :return: json data of the departure times
    :rtype: dict
    """
    # We use the overview page for the departure time
    url = f"https://www.kvb.koeln/haltestellen/overview/{station_id}/"
    req = requests.get(url, headers=_random_user_agent())
    soup = BeautifulSoup(req.text, "lxml")
    tables = soup.find_all("table")
    if not tables:
        logger.warning(f'can not get info for station {station_id}')
        return {
            'status': 200,
            'data': []
        }
    else:
        tables = tables[0]
        logger.debug(f'got timetable for {station_id}: {tables}')

    # define the column names of the table
    fields = ['line', 'terminal', 'departures_in']

    departures = [
        dict(
            zip(fields, [cell.text.replace('\u00a0','') for cell in row("td")])
        )
        for row in tables('tr')
    ]

    return {
        'status': 200,
        'data': departures
    }


@app.route("/")
def index():
    output = {
        "utc_time": datetime.utcnow(),
        "methods": {
            "departures": "/stations/{station_id}/departures/",
            "stations": "/stations/"
        }
    }
    return json.dumps(output)

@app.route("/stations/")
@cached()
def stations_list():
    return json.dumps(_STATIONS)

@app.route("/stations/<int:station_id>/departures/")
def station_departuress(station_id):
    details = get_departures(station_id)
    return json.dumps(details)

# Add CORS header to every request
@app.after_request
def add_cors(resp):
    resp.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin','*')
    resp.headers['Access-Control-Allow-Credentials'] = 'true'
    resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS, GET'
    resp.headers['Access-Control-Allow-Headers'] = request.headers.get('Access-Control-Request-Headers', 'Authorization' )
    if app.debug:
        resp.headers['Access-Control-Max-Age'] = '1'
    return resp

if __name__ == "__main__":
    # app.config["DEBUG"] = True
    # app.run(host='0.0.0.0', port=8080)
    app.run(threaded=True, port=5000)
