import logging
import os
import re
from datetime import datetime, timedelta
from functools import wraps
import pytz

import requests
from bs4 import BeautifulSoup
from werkzeug.contrib.cache import SimpleCache

from flask import Flask, json, request
from fuzzywuzzy import fuzz, process
from utils.fetch import random_user_agent as _random_user_agent
from utils.parser import parse_time as _parse_time

logger = logging.getLogger('app')


__cwd__ = os.getcwd()
__location__ = os.path.realpath(
    os.path.join(__cwd__, os.path.dirname(__file__))
)

with open(os.path.join(__location__, 'utils', 'stations.json'), 'r') as fp:
    _STATIONS = json.load(fp)

_INVERSE_STATIONS = {value:key for key, value in _STATIONS.items()}

app = Flask(__name__)

cache = SimpleCache()


def search_station(st):
    """
    search_station searches among the existing database of the stations and finds the best match of the input

    :param st: input station name to be searched
    :type st: str
    :return: best match of the station name and id
    :rtype: str
    """

    res = []
    for key, val in _STATIONS.items():
        score = fuzz.token_set_ratio(st, key)
        res.append(
            {
                'station': key,
                'score': score,
                'station_id': val
            }
        )
    if not res:
        return {}
    else:
        res = sorted(res, key=lambda k: k['score'], reverse=True)
        res = res[0]
        return res


def cached(timeout=30, key='view/%s'):
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


def get_departures(station):
    """
    get_departures extracts the departure time at the station

    :param station_id: id of the station, e.g., 46 is Drehbrucke
    :type station_id: int
    :return: json data of the departure times
    :rtype: dict
    """

    # We use the overview page for the departure time
    url = f"https://www.kvb.koeln/haltestellen/overview/{station}/"
    req = requests.get(url, headers=_random_user_agent())
    soup = BeautifulSoup(req.text, "lxml")
    tables = soup.find_all("table")
    if not tables:
        logger.warning(f'can not get info for station {station}')
        return {
            'status': 200,
            'data': []
        }
    else:
        tables = tables[0]
        logger.debug(f'got timetable for {station}: {tables}')

    # define the column names of the table
    fields = ['line', 'terminal', 'departures_in']

    departures = [
        dict(
            zip(fields, [cell.text for cell in row("td")])
        )
        for row in tables('tr')
    ]

    res_data = []
    kvb_local_time = datetime.now(pytz.timezone('Europe/Berlin'))
    for dep in departures:
        dep_parse_time = {}
        try:
            dep_parse_time = _parse_time(dep.get('departures_in',''))
            dep['departures_in'] = '{value} {unit}'.format(
                **dep_parse_time
            )
        except Exception as e:
            logger.error(f'Could not parse departure time: {e}')

        if dep_parse_time:
            dep_departure_time = (
                kvb_local_time + timedelta(minutes=dep_parse_time.get('value'))
            ).strftime('%H:%M')
            dep['departures_at'] = dep_departure_time

        res_data.append(dep)

    res_dict = {
        'status': 200,
        'local_time': kvb_local_time.isoformat(),
        #'data': res_data,
        'departures': res_data
    }

    return res_dict


def retrieve_departures(station):
    """
    retrieve_departures retrieves departures at a station for a given station id or name
    """
    message = 'successfully downloaded info'
    if isinstance(station, (int, float)) or station.isdigit():
        station_id = int(float(station))
        station = _INVERSE_STATIONS.get(station_id)
    elif isinstance(station, str) and (not station.isdigit()):
        station = station.lower()
        if station.isdigit():
            station_id = station
        elif _STATIONS.get(station):
            station_id = _STATIONS.get(station)
        else:
            station_searched = search_station(station)
            station_id = station_searched.get('station_id')
            message = f'{message}; checking departures for  {station_searched}'
            station = station_searched.get('station')
    else:
        return json.dumps({
            'status': 200,
            'message': 'input station {} is invalid'.format(station),
            'data': []
        })

    departures = get_departures(station_id)
    departures['message'] = message
    departures['station'] = {'name': station, 'id': station_id}

    return departures


@app.route("/")
def index():
    output = {
        "local_time": datetime.now(tz=pytz.timezone('Europe/Berlin')).isoformat(),
        "methods": {
            "departures": "/station/{station_id}/departures/",
            "stations": "/station/"
        }
    }
    return json.dumps(output)

@app.route("/station/")
@cached()
def stations_list():
    return json.dumps(_STATIONS)

@app.route("/station/<int:station>/departures/")
@app.route("/station/<station>/departures/")
def get_station_departures(station):

    departures = retrieve_departures(station)
    return json.dumps(departures)


@app.route("/station", methods = ['POST'])
def post_station_departures():

    data = request.json # a multidict containing POST data
    station = data.get("station")

    if not isinstance(station, str):
        try:
            station = str(station)
        except Exception as e:
            raise Exception("Can not convert input station into str")

    departures = retrieve_departures(station)

    return json.dumps(departures)


def format_slack_kvb_departures(departures, line=None):

    dep_schedule = departures.get('departures', [])
    dep_station = departures.get('station',{})
    dep_station_name = dep_station.get('name')
    dep_station_id = dep_station.get('id')

    dep_schedule_blocks = [
		{
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": "KVB Schedule for *{}* (station id: {})".format(dep_station_name, dep_station_id)
			}
		}
    ]

    if not line:
        all_lines = set([i.get('line') for i in dep_schedule])
    else:
        all_lines = {line}

    dep_schedule_by_lines = {}
    for line in all_lines:
        i_schedule = []
        for i in dep_schedule:
            if i.get('line') == line:
                i_schedule.append(i)
        dep_schedule_by_lines[line] = i_schedule
    for line, val in dep_schedule_by_lines.items():

        dep_schedule_blocks.append(
            {
                "type": "divider"
            }
        )
        line_text = ""
        for i in val:
            line_text = line_text + "    - *{}*: at {} in {}\n".format(
                        i.get('terminal'), i.get('departures_at'), i.get('departures_in')
                    )

        dep_schedule_blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Line *{line}*\n" + line_text
                }
            }
        )

    dep_schedule_blocks.append(
        {
			"type": "context",
			"elements": [
				{
					"type": "mrkdwn",
					"text": "by */kvb* command: built with love"
				}
			]
		}
    )


    res = {
        "response_type": "in_channel",
        "blocks": dep_schedule_blocks
    }

    return res


@app.route("/slack/kvb/departures", methods=["POST"])
def slack_kvb_departures():

    data = request.form
    # TODO: validate token
    token = data.get('token', None)
    command = data.get('command', None)
    text = data.get('text', '')

    line = None

    if isinstance(text, str):
        text = text.strip()

    logger.debug("slack payload:: text: ",text)

    if not text.startswith('-'):
        if ' ' in text:
            re_station = re.compile(r'(\S+)\s+(\S+)')
            station_line = re_station.findall(text)
            if station_line:
                station, line = station_line[0]
        else:
            station = text
    else:
        query = text

    if not isinstance(station, str):
        try:
            station = str(station)
        except Exception as e:
            raise Exception("Can not convert input station into str")

    departures = retrieve_departures(station)

    return format_slack_kvb_departures(departures, line=line)

# Add CORS header to every request
# CORS allows us to use the api cross domain
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
    app.config['DEBUG'] = True
    app.run(threaded=True, port=5000)
