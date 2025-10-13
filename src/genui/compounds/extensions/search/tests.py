import json

from django.urls import reverse
from rest_framework.test import APITestCase

from genui.projects.tests import ProjectMixIn


class ChEMBLMolSetTestCase(ProjectMixIn, APITestCase):
    """
    We use the 'ProjectMixIn' class to automatically get
    a project instance initialized before our tests.
    It will become available from 'self.project'
    """

    def test_json_upload(self):
        post_data = {
            "molecules": "CCO",
        }

        # create new compound set instance
        response = self.client.post(reverse('jsonSet-list'), post_data, format='json')
        self.assertEqual(response.status_code, 201)

