import json
import os
import re

import requests
from bs4 import BeautifulSoup

from fetch import random_user_agent as _random_user_agent

__cwd__ = os.getcwd()
__location__ = os.path.realpath(
    os.path.join(__cwd__, os.path.dirname(__file__))
)

with open(os.path.join(__location__, 'stations.json'), 'r') as fp:
    _MANUAL_STATIONS = json.load(fp)

def get_stations():
    """
    get_stations retrieve a list of stations in cologne

    :return: dictionary of stations with names and id
    :rtype: dict
    """
    re_parse_url = re.compile(r'haltestellen/overview/(?P<station_id>.*?)/')
    url = "https://www.kvb.koeln/haltestellen/overview/"
    req = requests.get(url, headers=_random_user_agent())
    soup = BeautifulSoup(req.text, 'lxml')
    soup_a = soup.find_all('a')
    soup_a = [i for i in soup_a if 'haltestellen/overview/' in i['href']]

    stations = {}

    for a in soup_a:
        href = a['href']
        station_id = re_parse_url.findall(href)
        station_name = a.text
        if station_id:
            station_id = station_id[0]
            stations[station_name] =  station_id

    return stations





if __name__ == "__main__":
    print(_MANUAL_STATIONS)
    print(get_stations())
    print('END OF GAME')
