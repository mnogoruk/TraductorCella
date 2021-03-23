import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler
from django.conf import settings

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        response.data['status_code'] = response.status_code
    else:
        if not settings.TESTING:
            logger.error(f"Unexpected error.")
            response = Response(data={'detail': 'Unexpected error.', 'status_code': 500},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return None
    return response
