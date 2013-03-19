'''Simple test case '''

from django.test import TestCase
from profilehooks import timecall, profile
import urllib2
from django.contrib.auth.models import User


class SimpleTestCase(TestCase):
    ''' Simple test case '''

    @profile
    def test_something(self):
        ''' Dummy test '''   
        for i in xrange(1000):
            User(username='john_{}'.format(i))
