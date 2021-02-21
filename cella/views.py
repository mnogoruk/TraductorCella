import logging

from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
import logging
from .models import Test1, Test2
from rest_framework.authentication import BasicAuthentication
from cella.models import Test1, Test2

logger = logging.getLogger(__name__)


# Resources
class TestView(APIView):
    authentication_classes = (BasicAuthentication,)

    def get(self, request, *args, **kwargs):
        with transaction.atomic():
            t1 = Test1.objects.create(test='ew', var=23)
            t2 = Test2(tt='1', bb=2.3, v=t1)
            t3 = Test2(tt='2', bb=4.2, v=t1)
            a = [t2, t3]
            Test2.objects.bulk_create(a)

        return Response(data={"da": "yes"}, status=status.HTTP_200_OK)
