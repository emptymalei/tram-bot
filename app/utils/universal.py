import random


def flatten_json(y):
    '''Flattens the JSON data
    '''
    out = {}

    def flatten(x, name=''):
        if type(x) is dict:
            for a in x:
                flatten(x[a], name + a + '__')
        elif type(x) is list:
            i = 0
            for a in x:
                flatten(a, name + str(i) + '__')
                i += 1
        else:
            out[name[:-2]] = x

    flatten(y)

    return out


def retry_timer(which_retry, retry_base_interval, mode=None):
    """Calculate a random retry interval

    Args:
        mode(optional, default=None): specify the mode of retry time
            list of possible values: 'random', 'multiply', 'multirand'
    """

    if mode is None:
        mode = 'random'

    if mode == 'random':
        retry_wait_interval = retry_base_interval * random.random()
    elif mode == 'multiply':
        retry_wait_interval = which_retry * retry_base_interval
    elif mode == 'multirand':
        retry_wait_interval = which_retry * retry_base_interval * random.random()

    return {'mode': mode, 'interval': retry_wait_interval, 'retry': which_retry}
