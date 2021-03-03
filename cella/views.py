from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
import logging


logger = logging.getLogger(__name__)


class TestView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        logger.warning("WARNING")
        logger.debug("DEBUG")
        logger.info("INFO")
        logger.error("ERROR")
        print(request.data)

        return Response(data={"da": "yes"}, status=status.HTTP_200_OK)
