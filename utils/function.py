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
