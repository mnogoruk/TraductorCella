import logging

from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authentication import BasicAuthentication
from cella.models import Test1, Test2

logger = logging.getLogger(__name__)


class TestView(APIView):
    permission_classes = ()
    authentication_classes = ()

    def post(self, request, *args, **kwargs):
        logger.warning("WARNING")
        logger.debug("DEBUG")
        logger.info("INFO")
        logger.error("ERROR")
        print(request.data['ID'])
        print(request.data['price'])

        return Response(data={"da": "yes"}, status=status.HTTP_200_OK)
