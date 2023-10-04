import re
from datetime import datetime


def convert_str_to_camel(snake_str):
    parts = snake_str.split('_')
    return parts[0] + ''.join(x.title() for x in parts[1:])


def convert_str_to_pascal(snake_str):
    parts = snake_str.split('_')
    return ''.join(x.title() for x in parts[0:])


def convert_dict_to_camel(data: dict):
    new = {}
    for k, v in data.items():
        new_v = v
        if isinstance(v, dict):
            new_v = convert_dict_to_camel(v)
        elif isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
            new_v = list()
            for x in v:
                new_v.append(convert_dict_to_camel(x))
        new[convert_str_to_camel(k)] = new_v
    return new


def convert_dict_to_pascal(data: dict):
    new = {}
    for k, v in data.items():
        new_v = v
        if isinstance(v, dict):
            new_v = convert_dict_to_camel(v)
        elif isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
            new_v = list()
            for x in v:
                new_v.append(convert_dict_to_camel(x))
        new[convert_str_to_pascal(k)] = new_v
    return new


def convert_dict_to_snake(data: dict):
    new = {}
    for k, v in data.items():
        new_v = v
        if isinstance(v, dict):
            new_v = convert_dict_to_snake(v)
        elif isinstance(v, list):
            new_v = list()
            for x in v:
                new_v.append(convert_dict_to_snake(x))
        new[convert_str_to_snake(k)] = new_v
    return new


def convert_str_to_snake(camel_str):
    camel_str = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', camel_str)
    camel_str = re.sub('__([A-Z])', r'_\1', camel_str)
    camel_str = re.sub('([a-z0-9])([A-Z])', r'\1_\2', camel_str)
    return camel_str.lower()


def get_html_node_text(html_node):
    if html_node:
        return html_node.text.strip()
    return None


def convert_datetime_to_str(date):
    month = date.month
    if month < 10:
        month = '0' + str(month)
    day = date.day
    if day < 10:
        day = '0' + str(day)
    if date is None:
        return None
    return f'{date.year}-{month}-{day}'


def concetti_query_params_url_encode(query_params):
    return "&".join("%s=%s" % (k, v) for k, v in query_params.items())


def convert_str_to_datetime(date_str):
    date_pattern = r'(\d{1,2})/(\d{1,2})/(\d{4})'
    match = re.match(date_pattern, date_str)

    if match:
        day = match.group(1)
        month = match.group(2)
        year = match.group(3)

        formatted_date = f'{year}-{month.zfill(2)}-{day.zfill(2)}'
        return formatted_date
    else:
        return None
