from rest_framework import serializers
from collections import OrderedDict

from rest_framework.fields import empty
from rest_framework.validators import UniqueValidator

from .service import Providers, Resources
from .models import Resource, ResourceProvider, ResourceAction


class ProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceProvider
        fields = '__all__'


class ResourceActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceAction
        fields = '__all__'


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
    last_change_cost = serializers.DateTimeField('cost_time_stamp', read_only=True)
    last_change_amount = serializers.DateTimeField('amount_time_stamp', read_only=True)

    def to_representation(self, instance):
        if instance.provider_id is not None:
            provider = {
                'id': instance.provider_id,
                'name': instance.provider_name
            }
        else:
            provider = None
        data = {
            'id': instance.id,
            'name': instance.name,
            'external_id': instance.external_id,
            'cost': instance.cost,
            'amount': instance.amount,
            'provider': provider,
            'last_change_amount': instance.cost_time_stamp,
            'last_change_cost': instance.amount_time_stamp,
        }

        return data

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
        fields = ['id', 'name', 'external_id', 'provider', 'provider_name', 'cost', 'amount', 'last_change_amount', 'last_change_cost']
