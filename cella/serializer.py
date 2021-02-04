from rest_framework import serializers
from collections import OrderedDict

from rest_framework.fields import empty
from rest_framework.validators import UniqueValidator

from .service import Providers, Resources, Specifications
from .models import Resource, ResourceProvider, ResourceAction, Specification, SpecificationCategory


class ProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceProvider
        fields = '__all__'


class ResourceActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceAction
        fields = '__all__'


class ResourceWithUnverifiedCostSerializer(serializers.ModelSerializer):
    name = serializers.CharField(read_only=True)
    external_id = serializers.CharField(read_only=True)
    provider = ProviderSerializer(read_only=True, allow_null=True)
    old_cost = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    new_cost = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    amount = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    unverified = serializers.BooleanField()

    class Meta:
        model = Resource
        fields = ['id', 'name', 'external_id', 'provider', 'old_cost', 'new_cost', 'amount', 'unverified']


class ResourceSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=True)
    external_id = serializers.CharField(required=True,
                                        validators=[
                                            UniqueValidator(
                                                queryset=Resource.objects.defer('external_id').all()
                                            )
                                        ]
                                        )
    provider = ProviderSerializer(read_only=True, allow_null=True)
    provider_name = serializers.CharField(write_only=True, required=False, allow_null=True)
    cost = serializers.DecimalField(max_digits=8, decimal_places=2, required=False)
    amount = serializers.DecimalField(max_digits=8, decimal_places=2, required=False)
    last_change_cost = serializers.DateTimeField(read_only=True)
    last_change_amount = serializers.DateTimeField(read_only=True)

    def create(self, validated_data):
        service = Resources(request=validated_data.get('request'))
        resource, _ = service.create(
            resource_name=validated_data.get('name'),
            external_id=validated_data.get('external_id'),
            cost_value=validated_data.get('cost'),
            amount_value=validated_data.get('amount'),
            provider_name=validated_data.get('provider_name')
        )
        return resource

    def update(self, instance, validated_data):
        service = Resources(request=validated_data.get('request'))

        cost = validated_data.get('cost')
        amount = validated_data.get('amount')
        resource_name = validated_data.get('name')
        external_id = validated_data.get('external_id')
        provider_name = validated_data.get('provider_name')

        update_data = {}

        if resource_name is not None:
            update_data['resource_name'] = resource_name
        if external_id is not None:
            update_data['external_id'] = external_id
        if provider_name is not None:
            update_data['provider_name'] = provider_name

        resource, _ = service.update_fields(r_id=instance.id, **update_data)

        if cost is not None:
            service.set_cost(r_id=instance.id, cost_value=cost)
        if amount is not None:
            service.set_amount(r_id=instance.id, amount_value=amount)

        return resource

    class Meta:
        model = Resource
        fields = [
            'id',
            'name',
            'external_id',
            'provider',
            'provider_name',
            'cost',
            'amount',
            'last_change_amount',
            'last_change_cost']


class ResourceShortListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resource
        fields = ['id', 'name', 'external_id']


class SpecificationCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecificationCategory
        fields = '__all__'


class SpecificationResource(serializers.Serializer):
    resource = ResourceSerializer()
    amount = serializers.DecimalField(max_digits=8, decimal_places=2)


class SpecificationResourceCreateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=8, decimal_places=2)
    id = serializers.IntegerField()


class SpecificationDetailSerializer(serializers.ModelSerializer):
    resources = SpecificationResource(many=True, read_only=True)
    price = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, allow_null=True)
    price_time_stamp = serializers.DateTimeField(read_only=True)
    category_name = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    category = SpecificationCategorySerializer(read_only=True, required=False)
    is_active = serializers.BooleanField(read_only=True)
    resources_create = SpecificationResourceCreateSerializer(many=True, write_only=True)

    class Meta:
        model = Specification
        fields = '__all__'

    def create(self, validated_data):
        print(validated_data)
        spec = Specifications.create(
            name=validated_data['name'],
            product_id=validated_data['product_id'],
            price=validated_data['price'],
            resources=validated_data['resources_create'],
            category_name=validated_data['category_name'],
            user=validated_data['request'].user
        )
        return spec


class SpecificationListSerializer(serializers.ModelSerializer):
    category = SpecificationCategorySerializer()
    prime_cost = serializers.DecimalField(max_digits=8, decimal_places=2)
    price = serializers.DecimalField(max_digits=8, decimal_places=2)
    price_time_stamp = serializers.DateTimeField()

    class Meta:
        model = Specification
        fields = '__all__'


