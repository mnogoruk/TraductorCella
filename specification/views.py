from django.http import Http404
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView, CreateAPIView, RetrieveUpdateAPIView
from logging import getLogger

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from resources.models import Resource
from resources.service import Resources
from specification.models import Specification
from specification.serializer import SpecificationCategorySerializer, SpecificationDetailSerializer, \
    SpecificationListSerializer, SpecificationEditSerializer, SpecificationShortSerializer
from specification.service import Specifications
from utils.exception import NoParameterSpecified, ParameterExceptions, QueryError, UpdateError, AssembleError
from utils.pagination import StandardResultsSetPagination
from authentication.permissions import OfficeWorkerPermission, StorageWorkerPermission, DefaultPermission, \
    AdminPermission

logger = getLogger(__name__)


class SpecificationCategoryListView(ListAPIView):
    serializer_class = SpecificationCategorySerializer
    permission_classes = [IsAuthenticated, DefaultPermission]

    def get_queryset(self):
        try:
            return Specifications.categories()
        except Specifications.QueryError:
            logger.warning(f"category list error. | {self.__class__.__name__}", exc_info=True)


class SpecificationDetailView(RetrieveAPIView):
    serializer_class = SpecificationDetailSerializer
    permission_classes = [IsAuthenticated, DefaultPermission]

    def get_object(self):
        s_id = self.kwargs['s_id']
        try:
            specification = Specifications.detail(s_id)
        except Specification.DoesNotExist:
            logger.warning(f"'id' not specified | {self.__class__.__name__}", exc_info=True)
            raise Http404()
        self.check_object_permissions(request=self.request, obj=specification)

        return specification


class SpecificationListView(ListAPIView):
    serializer_class = SpecificationListSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAuthenticated, DefaultPermission]

    def get_queryset(self):
        try:
            return Specifications.list()
        except Specifications.QueryError:
            logger.warning(f"Query error | {self.__class__.__name__}", exc_info=True)
            raise QueryError()


class SpecificationCreateView(CreateAPIView):
    serializer_class = SpecificationDetailSerializer
    permission_classes = [IsAuthenticated, OfficeWorkerPermission]

    def perform_create(self, serializer):
        try:
            return serializer.save(request=self.request)
        except Specifications.QueryError:
            logger.warning(f"Create error | {self.__class__.__name__}", exc_info=True)
            raise QueryError()

    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class SpecificationEditView(RetrieveUpdateAPIView):
    serializer_class = SpecificationEditSerializer
    permission_classes = [IsAuthenticated, OfficeWorkerPermission]

    def perform_update(self, serializer):
        try:
            return serializer.save(user=self.request.user)
        except Specifications.EditError:
            logger.warning(f"Edit error | {self.__class__.__name__}", exc_info=True)
            raise UpdateError()

    def get_object(self):
        s_id = self.kwargs['s_id']
        try:
            resource = Resources.get(s_id)
        except Resource.DoesNotExist:
            logger.warning(f"Can`t get object 'Specification' with id: {s_id}. | {self.__class__.__name__}",
                           exc_info=True)
            raise Http404()
        self.check_object_permissions(request=self.request, obj=resource)


class SpecificationSetPriceView(APIView):
    permission_classes = [IsAuthenticated, AdminPermission]

    def post(self, request, *args, **kwargs):
        data = request.data
        try:
            s_id = data['id']
        except KeyError as ex:
            logger.warning(f"'id' not specified  | {self.__class__.__name__}", exc_info=True)
            raise NoParameterSpecified('id')
        try:
            value = data['price']
        except KeyError as ex:
            logger.warning(f"'price' not specified  | {self.__class__.__name__}", exc_info=True)
            raise NoParameterSpecified('price')
        if value is not None and s_id is not None:
            try:
                Specifications.set_price(specification=s_id, price=value, user=request.user)
            except Specifications.EditError:
                logger.warning(f"Set price error | {self.__class__.__name__}", exc_info=True)
            return Response(data={'id': s_id, 'price': value}, status=status.HTTP_202_ACCEPTED)
        else:
            raise NoParameterSpecified()


class SpecificationSetCoefficientView(APIView):
    permission_classes = [IsAuthenticated, AdminPermission]

    def post(self, request, *args, **kwargs):
        data = request.data
        try:
            s_id = data['id']
        except KeyError as ex:
            logger.warning(f"'id' not specified | {self.__class__.__name__}", exc_info=True)
            raise NoParameterSpecified('id')
        try:
            logger.warning(f"'coefficient' not specified | {self.__class__.__name__}", exc_info=True)
            value = data['coefficient']
        except KeyError as ex:
            logger.warning(f"'coefficient' not specified | {self.__class__.__name__}", exc_info=True)
            raise NoParameterSpecified('coefficient')
        if value is not None and s_id is not None:
            try:
                Specifications.set_coefficient(specification=s_id, coefficient=value, user=request.user)
            except Specifications.EditError:
                logger.warning(f"Set coefficient error | {self.__class__.__name__}", exc_info=True)
            return Response(data={'id': s_id, 'coefficient': value}, status=status.HTTP_202_ACCEPTED)
        else:
            raise NoParameterSpecified()


class SpecificationSetCategoryView(APIView):
    permission_classes = [IsAuthenticated, AdminPermission]

    def post(self, request, *args, **kwargs):
        data = request.data

        try:
            ids = data['ids']
        except KeyError as ex:
            logger.warning(f"'ids' not specified | {self.__class__.__name__}", exc_info=True)
            raise NoParameterSpecified('ids')

        if not isinstance(ids, list):
            logger.warning(f"'ids' has wrong type. Type: {type(ids)} | {self.__class__.__name__}")
            raise ParameterExceptions(detail="'ids' must be list object.")

        try:
            category = data['category']
        except KeyError as ex:
            logger.warning(f"'category' not specified | {self.__class__.__name__}", exc_info=True)
            raise NoParameterSpecified('category')

        Specifications.set_category_many(ids, category, request.user)
        return Response(data={'correct': True}, status=status.HTTP_202_ACCEPTED)


class SpecificationAssembleInfoView(APIView):
    permission_classes = [IsAuthenticated, DefaultPermission]

    def get(self, request, *args, **kwargs):
        s_id = self.kwargs['s_id']
        try:
            assembling_amount = Specifications.assemble_info(s_id)
        except Specifications.DoesNotExist:
            logger.warning(f"Can`t get object 'Specification' with id: {s_id}. | {self.__class__.__name__}",
                           exc_info=True)
            raise Http404

        return Response(data={'assembling_amount': assembling_amount}, status=status.HTTP_200_OK)


class SpecificationBuildSetView(APIView):
    permission_classes = [IsAuthenticated, StorageWorkerPermission]

    def post(self, request, *args, **kwargs):
        data = request.data
        try:
            s_id = data['id']
        except KeyError as ex:
            logger.warning(f"'id' not specified | {self.__class__.__name__}", exc_info=True)
            raise NoParameterSpecified(detail='id not specified.')
        try:
            amount = data['amount']
        except KeyError as ex:
            logger.warning(f"'cost' not specified | {self.__class__.__name__}", exc_info=True)
            raise NoParameterSpecified(detail='amount not specified.')

        from_resources = data.get('from_resources', False)
        try:
            Specifications.build_set(s_id, amount, from_resources, user=request.user)
        except Specifications.CantBuildSet:
            logger.warning(f"Building set error | {self.__class__.__name__}", exc_info=True)
            raise AssembleError()
        return Response(data={'correct': True}, status=status.HTTP_202_ACCEPTED)


class SpecificationBulkDeleteView(APIView):
    permission_classes = [IsAuthenticated, OfficeWorkerPermission]

    def post(self, request, *args, **kwargs):
        data = request.data
        try:
            ids = data['ids']
        except KeyError as ex:
            raise NoParameterSpecified('ids')
        if not isinstance(ids, list):
            raise ParameterExceptions(detail="'ids' must be list object.")
        try:
            Specifications.bulk_delete(ids, request.user)
        except Specifications.QueryError:
            logger.warning(f"Delete error | {self.__class__.__name__}", exc_info=True)
        return Response(data={'correct': True}, status=status.HTTP_202_ACCEPTED)


class SpecificationCreateCategoryView(CreateAPIView):
    permission_classes = [IsAuthenticated, OfficeWorkerPermission]

    serializer_class = SpecificationCategorySerializer


class SpecificationListShortView(ListAPIView):
    serializer_class = SpecificationShortSerializer

    def get_queryset(self):
        return Specifications.shortlist()


class SpecifiedVerifyPriceCount(APIView):
    permission_classes = [IsAuthenticated, DefaultPermission]

    def get(self, request, *args, **kwargs):
        return Response(data={'count': Specifications.verify_price_count()}, status=status.HTTP_202_ACCEPTED)
