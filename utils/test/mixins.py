from django.test import TestCase
from rest_framework import status


class ResponseTestCaseMixin:

    def assertExactResponseCode(self, response, code, msg=None):
        status_code = response.status_code
        if msg is not None:
            message = msg.format(status_code=status_code, response_data=response.data)
        else:
            message = None
        return self.assertEqual(status_code, code, message)

    def assertResponseInformational(self, response, msg=None):
        status_code = response.status_code
        if msg is not None:
            message = msg.format(status_code=status_code, response_data=response.data)
        else:
            message = None
        self.assertTrue(status.is_informational(status_code), message)

    def assertResponseSuccess(self, response, msg=None):
        status_code = response.status_code
        if msg is not None:
            message = msg.format(status_code=status_code, response_data=response.data)
        else:
            message = None
        self.assertTrue(status.is_success(status_code), message)

    def assertResponseRedirect(self, response, msg=None):
        status_code = response.status_code
        if msg is not None:
            message = msg.format(status_code=status_code)
        else:
            message = None
        self.assertTrue(status.is_redirect(status_code), message)

    def assertResponseClientError(self, response, msg=None):
        status_code = response.status_code
        if msg is not None:
            message = msg.format(status_code=status_code, response_data=response.data)
        else:
            message = None
        self.assertTrue(status.is_client_error(status_code), message)

    def assertResponseServerError(self, response, msg=None):
        status_code = response.status_code
        if msg is not None:
            message = msg.format(status_code=status_code)
        else:
            message = None
        self.assertTrue(status.is_server_error(status_code), message)
