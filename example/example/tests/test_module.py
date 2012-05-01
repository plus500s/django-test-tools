'''Simple test case '''

from django.test import TestCase
from test_tools.utils import model_factory
from django.contrib.auth.models import User


class SimpleTestCase(TestCase):
    ''' Simple test case '''

    def test_something(self):
        ''' Dummy test '''
        user = model_factory(User, save=True)
        self.assertTrue(user.id is not None)
