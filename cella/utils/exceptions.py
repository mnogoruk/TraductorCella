from rest_framework.exceptions import APIException


class WrongOrdering(APIException):
    status_code = 400
    default_detail = 'Wrong ordering options'
    default_code = 'bad_request'
