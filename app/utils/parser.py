import re

def parse_time(data):
    """
    parse_time parse the extracted time format from html and clean it up.

    >>> parse_time('7\u00a0Min')
    {'value': 7.0, 'unit': 'min'}
    >>> parse_time('7\u00a0min')
    {'value': 7.0, 'unit': 'min'}
    >>> parse_time('7\u00a0hour')
    {'value': 7.0, 'unit': 'hour'}
    >>> parse_time('Sofort')
    {'value': 0, 'unit': 'min'}

    :param data: [description]
    :type data: [type]
    :raises Exception: [description]
    :raises Exception: [description]
    :return: [description]
    :rtype: [type]
    """
    if not isinstance(data, str):
        try:
            data = str(data)
        except Exception as e:
            raise Exception(f'Could not convert {data} to str: {e}')

    data = data.strip().lower()

    if data == 'sofort':
        res = {
            'value': 0,
            'unit': 'min'
        }
    else:
        re_time_tab = re.compile('^(?P<value>.*?)[\u00a0|\s](?P<unit>.*?)$')

        time_value_unit = re_time_tab.findall(data)
        if time_value_unit:
            time_value_unit = time_value_unit[0]
            time_value_unit = [i.lower() for i in time_value_unit]

        fields = ['value', 'unit']

        res = dict(zip(fields, time_value_unit))
        try:
            res['value'] = int(float(res.get('value', '')))
        except Exception as e:
            raise Exception(f'Could not convert {res} value to float/int: {e}')

    return res