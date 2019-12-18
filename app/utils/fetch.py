import logging
import requests
import json
import random
import os

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

logging.basicConfig()
logger = logging.getLogger('fetch')


def random_user_agent():
    """
    """
    user_agent_list = [
        #Chrome
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36',
        'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36',
        'Mozilla/5.0 (Windows NT 5.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36',
        'Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36',
        'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36',
        'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36',
        'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36',
        #Firefox
        'Mozilla/4.0 (compatible; MSIE 9.0; Windows NT 6.1)',
        'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko',
        'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; WOW64; Trident/5.0)',
        'Mozilla/5.0 (Windows NT 6.1; Trident/7.0; rv:11.0) like Gecko',
        'Mozilla/5.0 (Windows NT 6.2; WOW64; Trident/7.0; rv:11.0) like Gecko',
        'Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko',
        'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.0; Trident/5.0)',
        'Mozilla/5.0 (Windows NT 6.3; WOW64; Trident/7.0; rv:11.0) like Gecko',
        'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0)',
        'Mozilla/5.0 (Windows NT 6.1; Win64; x64; Trident/7.0; rv:11.0) like Gecko',
        'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; WOW64; Trident/6.0)',
        'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; Trident/6.0)',
        'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0; .NET CLR 2.0.50727; .NET CLR 3.0.4506.2152; .NET CLR 3.5.30729)'
    ]

    return {'User-Agent': random.choice(user_agent_list)}


def luminati_proxies(config_path=None, proxy_config=None):
    """Access proxies
    """

    if proxy_config:
        if not isinstance(proxy_config, (dict)):
            try:
                proxy_config = json.loads(proxy_config)
            except Exception as ee:
                raise Exception(
                    'Could not load luminati config: {}; {}'.format(proxy_config, ee)
                    )
        config = proxy_config
    elif config_path:
        if not config_path.startswith('/'):
            __location__ = os.path.realpath(
                os.path.join(os.getcwd(), os.path.dirname(__file__))
                )
            config_full_path = os.path.join(__location__, config_path)
        else:
            config_full_path = config_path

        if not os.path.isfile(config_full_path):
            raise Exception('Config file not found in {}'.format(config_full_path))
        else:
            try:
                with open(config_full_path, 'r') as f:
                    config = json.loads(f.read())
            except Exception as ee:
                raise Exception(
                    'Config file found but could not load file: {}'.format(ee)
                    )
    else:
        raise Exception('Specify either the config (path) for luminati proxy!')

    config['session_id'] = random.random()

    session_id = random.random()
    super_proxy_url = 'http://{username}-session-{session_id}:{password}@zproxy.lum-superproxy.io:{port}'.format(
        **config
        )

    proxies = {
        'http': super_proxy_url,
        'https': super_proxy_url,
        }

    return proxies


def get_page_html(
    link,
    retry_params=None,
    headers=None,
    timeout=None,
    proxies=None,
    session=None,
    cookies=None,
    ):
    """Download page and save content
    """

    if cookies is None:
        cookies={'language': 'en'}

    if retry_params is None:
        retry_params = {}

    retry_params = {
        **{
            'retries': 5,
            'backoff_factor': 0.3,
            'status_forcelist': (500, 502, 504)
        },
        **retry_params
    }

    if headers is None:
        headers = random_user_agent()

    if timeout is None:
        timeout = (5, 14)

    if session is None:
        session = requests.Session()

    if proxies is None:
        proxies = {}

    retry = Retry(
        total=retry_params.get('retries'),
        read=retry_params.get('retries'),
        connect=retry_params.get('retries'),
        backoff_factor=retry_params.get('backoff_factor'),
        status_forcelist=retry_params.get('status_forcelist'),
    )

    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    page = session.get(link, headers=headers, proxies=proxies, cookies=cookies)

    status = page.status_code

    return {'status': status, 'page': page}
