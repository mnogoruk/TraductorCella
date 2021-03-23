import string
import random


def random_str(length):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))


def resource_amounts(objects, amount_list):
    ret = []
    for obj in objects:
        for pair in amount_list:
            if pair['id'] == obj.id:
                ret.append({'resource': obj, 'amount': pair['amount']})
                break
    return ret


def product_amounts(objects, amount_list):
    ret = []
    for obj in objects:
        for pair in amount_list:
            if pair['product_id'] == obj.product_id:
                ret.append({'specification': obj, 'amount': pair['amount']})
                break
    return ret


def dict_items_to_str(data):
    norm_data = {}
    if isinstance(data, dict):
        for pair in data.items():
            norm_data[dict_items_to_str(pair[0])] = dict_items_to_str(pair[1])
    elif data is not None:
        return str(data)
    else:
        return None
    return norm_data


def remove_empty_str(data):
    norm_data = {}
    if isinstance(data, dict):
        for pair in data.items():
            norm_data[pair[0]] = remove_empty_str(pair[1])
    elif data == '':
        return None
    return norm_data
