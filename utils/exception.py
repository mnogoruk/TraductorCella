from rest_framework.exceptions import APIException


class ParameterExceptions(APIException):
    status_code = 400
    default_detail = 'Parameter exceptions'
    default_code = 'bad_request'


class NoParameterSpecified(ParameterExceptions):
    default_detail = 'No parameter specified'

    def __init__(self, parameter_name=None, detail=None, code=None):

        _detail = None

        if parameter_name is not None:
            _detail = f"'{parameter_name}' not specified"
        if detail is not None:
            _detail = detail

        super(NoParameterSpecified, self).__init__(_detail, code)


class WrongParameterType(ParameterExceptions):
    default_detail = 'Wrong parameter type'

    def __init__(self, parameter_name=None, type_name=None, detail=None, code=None):
        if detail is not None:
            _detail = detail
        else:
            _detail = f"'{parameter_name}' must by '{type_name}' object"
        super(WrongParameterType, self).__init__(_detail, code)


class WrongParameterValue(ParameterExceptions):
    default_detail = 'Wrong value'

    def __init__(self, parameter_name=None, detail=None, code=None):
        _detail = None

        if parameter_name is not None:
            _detail = f"'{parameter_name}' has wrong value"
        if detail is not None:
            _detail = detail

        super(WrongParameterValue, self).__init__(_detail, code)


class CreateException(APIException):
    status_code = 500
    default_detail = 'Can`t create object'
    default_code = 'internal_error'


class FileException(APIException):
    status_code = 400
    default_detail = 'Fail error'
    default_code = 'bad_request'


class CreationError(APIException):
    status_code = 400
    default_detail = 'Unexpected error while editing object'
    default_code = 'bad_request'


class UpdateError(APIException):
    status_code = 400
    default_detail = 'Unexpected error while updating object'
    default_code = 'bad_request'


class DoesNotExist(APIException):
    status_code = 500
    default_detail = 'Object or query does not exist'
    default_code = 'internal_error'


class QueryError(APIException):
    status_code = 500
    default_code = 'internal_error'
    default_detail = 'Can`t manage query'


class AssembleError(APIException):
    status_code = 400
    default_code = 'bad_request'
    default_detail = 'Assembling error'
