from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import Resource, ResourceAction, ResourceProvider, ResourceDelivery
from .service import Resources


class ResourceProviderSerializer(serializers.ModelSerializer):
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
    provider = ResourceProviderSerializer(read_only=True, allow_null=True)
    old_cost = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    new_cost = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    verified = serializers.BooleanField()

    class Meta:
        model = Resource
        fields = ['id', 'name', 'external_id', 'provider', 'old_cost', 'new_cost', 'amount', 'verified']


class ResourceSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=True)
    external_id = serializers.CharField(required=True, validators=[
        UniqueValidator(
            queryset=Resource.objects.values('external_id').all()
        )
    ])
    provider = ResourceProviderSerializer(read_only=True, allow_null=True)
    provider_name = serializers.CharField(write_only=True, required=False, allow_null=True, default=None,
                                          allow_blank=True)
    cost = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, min_value=0, allow_null=True)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, min_value=0, allow_null=True)
    last_change_cost = serializers.DateTimeField(read_only=True)
    last_change_amount = serializers.DateTimeField(read_only=True)
    verified = serializers.BooleanField(allow_null=True, read_only=True)
    storage_place = serializers.CharField(allow_null=True, required=False)

    def create(self, validated_data):
        resource = Resources.create(
            resource_name=validated_data.get('name'),
            external_id=validated_data.get('external_id'),
            cost_value=validated_data.get('cost'),
            amount_value=validated_data.get('amount'),
            provider_name=validated_data.get('provider_name'),
            storage_place=validated_data.get('storage_place'),
            user=validated_data.get('request').user
        )
        return resource

    def update(self, instance, validated_data):

        cost = validated_data.get('cost')
        amount = validated_data.get('amount')
        resource_name = validated_data.get('name')
        external_id = validated_data.get('external_id')
        provider_name = validated_data.get('provider_name')
        user = validated_data.get('request').user
        update_data = {'user': user}

        if resource_name is not None:
            update_data['resource_name'] = resource_name
        if external_id is not None:
            update_data['external_id'] = external_id
        if provider_name is not None:
            update_data['provider_name'] = provider_name

        resource = Resources.update_fields(instance, **update_data)

        if cost is not None:
            Resources.set_cost(instance, cost_value=cost, user=user)

        if amount is not None:
            Resources.set_amount(instance, amount_value=amount, user=user)

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
            'amount_limit',
            'storage_place',
            'last_change_amount',
            'last_change_cost',
            'verified']


class ResourceShortSerializer(serializers.ModelSerializer):
    cost = serializers.DecimalField(max_digits=12, decimal_places=2)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        model = Resource
        fields = ['id', 'name', 'external_id', 'cost', 'amount']


class ResourceDeliverySerializer(serializers.ModelSerializer):
    provider_name = serializers.CharField(max_length=100)
    cost = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, min_value=0, allow_null=True)

    class Meta:
        model = ResourceDelivery
        fields = ['id', 'resource', 'provider_name', 'cost', 'amount', 'comment', 'time_stamp']

    def create(self, validated_data):
        return Resources.make_delivery(**validated_data)
