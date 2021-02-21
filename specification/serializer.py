from rest_framework import serializers

from resources.serializer import ResourceShortSerializer
from specification.models import SpecificationCategory, Specification
from specification.service import Specifications


class SpecificationCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecificationCategory
        fields = '__all__'


class SpecificationResourceSerializer(serializers.Serializer):
    resource = ResourceShortSerializer()
    amount = serializers.DecimalField(max_digits=8, decimal_places=2)

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class SpecificationShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Specification
        fields = ['name', 'product_id', 'id', 'price']


class SpecificationResourceCreateUpdateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=8, decimal_places=2)
    id = serializers.IntegerField()

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class SpecificationDetailSerializer(serializers.ModelSerializer):
    resources = SpecificationResourceSerializer(many=True, read_only=True, allow_null=True)
    price = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True, min_value=0)
    coefficient = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True,
                                           min_value=0)
    category_name = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    category = SpecificationCategorySerializer(read_only=True, required=False)
    is_active = serializers.BooleanField(read_only=True)
    resources_create = SpecificationResourceCreateUpdateSerializer(many=True, write_only=True)
    verified = serializers.BooleanField(read_only=True, allow_null=True)
    amount = serializers.IntegerField(allow_null=True, required=False, default=0, min_value=0)
    available_to_assemble = serializers.IntegerField(read_only=True, allow_null=True)

    def validate_resources_create(self, value):
        if len(value) == 0:
            raise serializers.ValidationError('Resources can`t be empty.')
        else:
            ids = []
            for pair in value:
                if pair['id'] in ids:
                    raise serializers.ValidationError('Resource duplicates.')
                ids.append(pair['id'])
        return value

    class Meta:
        model = Specification
        fields = '__all__'

    def create(self, validated_data):
        spec = Specifications.create(
            name=validated_data['name'],
            product_id=validated_data['product_id'],
            price=validated_data['price'],
            coefficient=validated_data['coefficient'],
            resources=validated_data['resources_create'],
            category_name=validated_data['category_name'],
            amount=validated_data['amount'],
            user=validated_data['request'].user
        )
        return spec


class SpecificationListSerializer(serializers.ModelSerializer):
    category = SpecificationCategorySerializer()
    prime_cost = serializers.DecimalField(max_digits=8, decimal_places=2)
    price = serializers.DecimalField(max_digits=8, decimal_places=2)
    coefficient = serializers.DecimalField(max_digits=8, decimal_places=2)
    verified = serializers.BooleanField(allow_null=True, read_only=True)
    amount = serializers.IntegerField(allow_null=True)

    class Meta:
        model = Specification
        fields = '__all__'


class SpecificationShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Specification
        fields = '__all__'


class SpecificationEditSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=False, allow_null=True)
    product_id = serializers.CharField(required=False, allow_null=True)
    category_name = serializers.CharField(required=False, allow_null=True, write_only=True)
    price = serializers.DecimalField(required=False, allow_null=True, max_digits=8, decimal_places=2)
    coefficient = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, allow_null=True)
    resource_to_add = SpecificationResourceCreateUpdateSerializer(required=False, many=True, default=[],
                                                                  write_only=True)
    resource_to_delete = serializers.ListField(required=False, default=[], write_only=True)
    resources = SpecificationResourceSerializer(many=True, read_only=True)
    category = SpecificationCategorySerializer(read_only=True)

    def update(self, instance, validated_data):
        return Specifications.edit(instance, **validated_data)

    class Meta:
        model = Specification
        fields = '__all__'
