from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .service import Resources, Specifications, Orders
from .models import Resource, ResourceProvider, ResourceAction, Specification, SpecificationCategory, File, Order, \
    OrderSpecification


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
    verified = serializers.BooleanField()

    class Meta:
        model = Resource
        fields = ['id', 'name', 'external_id', 'provider', 'old_cost', 'new_cost', 'amount', 'verified']


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
    provider_name = serializers.CharField(write_only=True, required=False, allow_null=True, default=None)
    cost = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, min_value=0, allow_null=True)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, min_value=0, allow_null=True)
    last_change_cost = serializers.DateTimeField(read_only=True)
    last_change_amount = serializers.DateTimeField(read_only=True)
    verified = serializers.BooleanField(allow_null=True, read_only=True)

    def create(self, validated_data):
        resource = Resources.create(
            resource_name=validated_data.get('name'),
            external_id=validated_data.get('external_id'),
            cost_value=validated_data.get('cost'),
            amount_value=validated_data.get('amount'),
            provider_name=validated_data.get('provider_name'),
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
            'last_change_amount',
            'last_change_cost',
            'verified']


class ResourceShortSerializer(serializers.ModelSerializer):
    cost = serializers.DecimalField(max_digits=8, decimal_places=2)
    amount = serializers.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        model = Resource
        fields = ['id', 'name', 'external_id', 'cost', 'amount']


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
    coefficient = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True, min_value=0)
    category_name = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    category = SpecificationCategorySerializer(read_only=True, required=False)
    is_active = serializers.BooleanField(read_only=True)
    resources_create = SpecificationResourceCreateUpdateSerializer(many=True, write_only=True)
    verified = serializers.BooleanField(read_only=True, allow_null=True)
    amount = serializers.IntegerField(allow_null=True, required=False, default=0, min_value=0)

    def validate_resources_create(self, value):
        if len(value) == 0:
            raise serializers.ValidationError("List can`t br empty.")
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


class OrderSpecificationSerializer(serializers.ModelSerializer):
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


class OrderSerializer(serializers.ModelSerializer):
    order_specification = OrderSpecificationSerializer(many=True, read_only=True)
    specifications_create = OrderSpecificationCreateUpdateSerializer(write_only=True, many=True)

    def create(self, validated_data):
        order = Orders.create(
            external_id=validated_data['external_id'],
            source=validated_data['source'],
            products=validated_data['specifications_create']
        )
        return order

    class Meta:
        model = Order
        fields = '__all__'


class FileSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = '__all__'
