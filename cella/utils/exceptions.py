from rest_framework.exceptions import APIException


class NoParameter(APIException):
    status_code = 400
    default_detail = 'No parameter'
    default_code = 'bad_request'
