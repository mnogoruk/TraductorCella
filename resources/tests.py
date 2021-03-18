from rest_framework.test import APITestCase
from django.forms.models import model_to_dict

from .models import Resource, ResourceProvider
from utils.test.mixins import ResponseTestCaseMixin
from utils.function import dict_items_to_str


class ResourceCreateTest(ResponseTestCaseMixin, APITestCase):
    label = None
    request_data = {}
    resource = None

    def testCorrectRequest(self):
        test_data = [
            {
                "name": "Resource 1",
                "external_id": 1,
            },
            {
                "name": "resource 3",
                "external_id": "3",
                "amount": 40,
                "cost": 20.1
            },
            {
                "name": "resource 4",
                "external_id": "4",
                "amount": 34.1,
                "cost": 99.1
            },
            {
                "name": "resource 5",
                "external_id": 5,
                "provider_name": "Test provider"
            },
            {
                "name": "resource 7",
                "external_id": 7,
                "cost": None,
                "amount": None,
                "amount_limit": None,
                "provider_name": None
            },
            {
                "name": "resource 8",
                "external_id": 8,
                "amount_limit": 100
            }
        ]
        for data in test_data:
            self.setRequestData(data)
            self.createAndCheckResource()

    def setRequestData(self, data):
        self.request_data = data

    def createAndCheckResource(self):
        response = self.postResourceData()

        self.normalizeRequestData()

        self.assertResponseSuccess(response, "{status_code}, {response_data}")
        self.assertCorrectResponse(response)
        self.assertResourceExists(response.data['id'])
        self.setResourceById(response.data['id'])
        self.assertRequestDataMatchResourceData()

    def setResourceById(self, resource_id):
        self.resource = Resource.objects.select_related('provider').get(id=resource_id)

    def postResourceData(self):
        response = self.client.post('/resource/create/', data=self.request_data, format='json')
        return response

    def normalizeRequestData(self):
        self.request_data = dict_items_to_str(self.request_data)

        for pair in self.request_data.items():
            if pair[0] in ['amount', 'cost'] and (pair[1] == '' or pair[1] is None):
                self.request_data[pair[0]] = 0.0
            if pair[0] == 'amount_limit' and (pair[1] == '' or pair[1] is None):
                self.request_data[pair[0]] = 10.0
            if pair[0] == 'provider_name' and (pair[1] == '' or pair[1] is None):
                self.request_data[pair[0]] = None

    def assertCorrectResponse(self, response):
        response_data = response.data
        request_data = self.request_data

        self.assertEqual(request_data['name'], response_data['name'])
        self.assertEqual(request_data['external_id'], response_data['external_id'])

        if 'amount' in request_data:
            self.assertEqual(float(request_data['amount']), float(response_data['amount']))
        else:
            self.assertEqual(float(response_data['amount']), .0)
        if 'amount_limit' in request_data:
            self.assertEqual(float(request_data['amount_limit']), float(response_data['amount_limit']))
        else:
            self.assertEqual(float(response_data['amount_limit']), 10.0)
        if 'cost' in request_data:
            self.assertEqual(float(request_data['cost']), float(response_data['cost']))
        else:
            self.assertEqual(float(response_data['cost']), .0)
        if 'provider_name' in request_data:
            if request_data['provider_name'] is not None:
                self.assertIsNotNone(response_data['provider'])
                self.assertEqual(request_data['provider_name'], response_data['provider']['name'])
            else:
                self.assertIsNone(response_data['provider'])
        else:
            self.assertIsNone(response_data['provider'])

    def assertRequestDataMatchResourceData(self):
        resource = self.resource
        request_data = self.request_data

        self.assertEqual(request_data['name'], resource.name)
        self.assertEqual(request_data['external_id'], resource.external_id)

        if 'amount' in request_data:
            self.assertEqual(float(request_data['amount']), float(resource.amount))
        else:
            self.assertEqual(resource.amount, .0)
        if 'amount_limit' in request_data:
            self.assertEqual(float(request_data['amount_limit']), float(resource.amount_limit))
        else:
            self.assertEqual(resource.amount_limit, 10.0)
        if 'cost' in request_data:
            self.assertEqual(float(request_data['cost']), float(resource.cost))
        else:
            self.assertEqual(resource.cost, .0)
        if 'provider_name' in request_data:
            if request_data['provider_name'] is not None:
                self.assertProviderExists(request_data['provider_name'])
                self.assertIsNotNone(resource.provider)
                self.assertEqual(request_data['provider_name'], resource.provider.name)
            else:
                self.assertIsNone(resource.provider)
        else:
            self.assertIsNone(resource.provider)

    def assertResourceExists(self, resource_id):
        self.assertTrue(Resource.objects.filter(id=resource_id).exists())

    def assertProviderExists(self, provider_name):
        self.assertTrue(ResourceProvider.objects.filter(name=provider_name).exists())

    def getLabel(self):
        return self.label or self.request_data.get('name') or self.request_data.get('id')
