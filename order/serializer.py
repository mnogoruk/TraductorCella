from rest_framework import serializers

from order.models import OrderSpecification, OrderSource, Order
from order.service import Orders
from specification.serializer import SpecificationShortSerializer


class OrderSpecificationSerializer(serializers.ModelSerializer):
    specification = SpecificationShortSerializer()

    class Meta:
        model = OrderSpecification
        fields = ['specification', 'amount', 'assembled']


class OrderSpecificationCreateUpdateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=8, decimal_places=2)
    product_id = serializers.CharField()

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class OrderSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderSource
        fields = '__all__'


class OrderSerializer(serializers.ModelSerializer):
    order_specification = OrderSpecificationSerializer(many=True, read_only=True)
    specifications_create = OrderSpecificationCreateUpdateSerializer(write_only=True, many=True)
    source = OrderSourceSerializer(read_only=True)
    source_name = serializers.CharField(max_length=100, write_only=True, allow_null=True, required=False,
                                        allow_blank=True)
    missing_resources = serializers.ListField(read_only=True, allow_null=True)
    missing_specifications = serializers.ListField(read_only=True, allow_null=True)

    def create(self, validated_data):
        order = Orders.create(
            external_id=validated_data['external_id'],
            source=validated_data['source_name'],
            products=validated_data['specifications_create'],
            user=validated_data['request'].user
        )
        return order

    def validate_specifications_create(self, value):
        if len(value) == 0:
            raise serializers.ValidationError('Products can`t be empty.')
        else:
            specs = []
            for pair in value:
                if pair['product_id'] in specs:
                    raise serializers.ValidationError('Products duplicates.')
                else:
                    specs.append(pair['product_id'])
        return value

    class Meta:
        model = Order
        fields = '__all__'
        read_only_fields = ['status']

