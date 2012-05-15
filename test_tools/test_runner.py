''' Custom test runner for `tests` folder support '''

import os
import pkgutil

from django.test import TestCase
from django.test.simple import DjangoTestSuiteRunner, reorder_suite, \
    build_suite, dependency_ordered
from django.db.models import get_app
from django.utils import unittest
from django.utils.unittest.loader import defaultTestLoader
from django.conf import settings
from django.utils.importlib import import_module
from django.db.backends.creation import TEST_DATABASE_PREFIX


def is_custom_test_package(module):
    ''' Check if test package contain other tests '''

    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if isinstance(attr, type) and issubclass(attr, unittest.TestCase):
            return False
    return hasattr(module, '__path__')


def get_test_module(app_name):
    ''' Import tests module '''
    module_name = '.'.join([app_name, 'tests'])
    try:
        return import_module(module_name)
    except ImportError, exception:
        if exception.message == 'No module named tests':
            raise ImportError('No module named {0}'.format(module_name))


def get_test_db_name(connection):
    if connection.settings_dict['TEST_NAME']:
        return connection.settings_dict['TEST_NAME']
    return TEST_DATABASE_PREFIX + connection.settings_dict['NAME']


class PersistentTestDatabaseMixin(object):
    ''' Skip database recreation '''

    def _get_test_db_name(self, connection):
        """
        Internal implementation - returns the name of the test DB that will be
        created. Only useful when called from create_test_db() and
        _create_test_db() and when no external munging is done with the 'NAME'
        or 'TEST_NAME' settings.
        """
        return get_test_db_name(connection)

    def reopen_connection(self, connection):
        ''' Reopen connection and check for database features '''
        connection.close()
        connection.settings_dict["NAME"] = self._get_test_db_name(connection)
        connection.features.confirm()
        connection.cursor()

    def setup_databases(self, **kwargs):
        ''' Skip database creation. Just return the right connections '''
        from django.db import connections, DEFAULT_DB_ALIAS

        # First pass -- work out which databases actually need to be created,
        # and which ones are test mirrors or duplicate entries in DATABASES
        mirrored_aliases = {}
        test_databases = {}
        dependencies = {}
        for alias in connections:
            connection = connections[alias]
            if connection.settings_dict['TEST_MIRROR']:
                # If the database is marked as a test mirror, save
                # the alias.
                mirrored_aliases[alias] = connection.settings_dict[
                                                                'TEST_MIRROR']
            else:
                # Store a tuple with DB parameters that uniquely identify it.
                # If we have two aliases with the same values for that tuple,
                # we only need to create the test database once.
                item = test_databases.setdefault(
                    connection.creation.test_db_signature(),
                    (connection.settings_dict['NAME'], [])
                )
                item[1].append(alias)

                if 'TEST_DEPENDENCIES' in connection.settings_dict:
                    dependencies[alias] = connection.settings_dict[
                                                        'TEST_DEPENDENCIES']
                else:
                    if alias != DEFAULT_DB_ALIAS:
                        dependencies[alias] = connection.settings_dict.get(
                                    'TEST_DEPENDENCIES', [DEFAULT_DB_ALIAS])

        # Second pass -- actually create the databases.
        old_names = []
        mirrors = []
        for signature, (db_name, aliases) in dependency_ordered(
                                        test_databases.items(), dependencies):
            connection = connections[aliases[0]]
            old_names.append((connection, db_name, True))
            self.reopen_connection(connection)
            for alias in aliases[1:]:
                connection = connections[alias]
                if db_name:
                    old_names.append((connection, db_name, False))
                    connection.settings_dict['NAME'] = self._get_test_db_name(
                                                                    connection)
                else:
                    # If settings_dict['NAME'] isn't defined, we have a backend
                    # where the name isn't important -- e.g., SQLite, which
                    # uses :memory:.
                    # Force create the database instead of assuming it's a
                    # duplicate.
                    self.reopen_connection(connection)
                    old_names.append((connection, db_name, True))

        for alias, mirror_alias in mirrored_aliases.items():
            mirrors.append((alias, connections[alias].settings_dict['NAME']))
            connections[alias].settings_dict['NAME'] = connections[
                                            mirror_alias].settings_dict['NAME']

        return old_names, mirrors

    def teardown_databases(self, old_config, **kwargs):
        ''' Don't delete database on the end of tests '''
        pass


class DiscoveryDjangoTestSuiteRunner(PersistentTestDatabaseMixin,
                                                        DjangoTestSuiteRunner):
    """A test suite runner that uses unittest2 test discovery."""

    def load_custom_test_package(self, module, app_name):
        ''' Load custom test package from module and app '''

        for importer, module_name, ispkg in pkgutil.iter_modules(
                                [os.path.dirname(module.__file__)]):
            try:
                import_module('.'.join([app_name, 'tests']))
            except ImportError, e:
                pass
            else:
                module = import_module('.'.join([app_name, 'tests',
                                             module_name]))
                yield defaultTestLoader.loadTestsFromModule(module)

    def load_from_app(self, app_name):
        ''' Yielding a suite from application '''
        app = get_app(app_name.split('.')[-1])
        suite = build_suite(app)
        if suite.countTestCases():
            yield suite
        else:
            test_module = get_test_module(app_name)
            if is_custom_test_package(test_module):
                for test in self.load_custom_test_package(test_module,
                                                          app_name):
                    yield test

    def get_apps(self):
        try:
            return settings.PROJECT_APPS
        except AttributeError:
            return settings.INSTALLED_APPS

    def build_suite(self, test_labels, extra_tests=None, **kwargs):
        suite = unittest.TestSuite()
        if test_labels:
            for test_label in test_labels:
                # Handle case when app defined with dot
                if '.' in test_label and test_label not in self.get_apps():
                    app_name = test_label.split('.')[0]
                    for app_label in self.get_apps():
                        if test_label.startswith(app_label):
                            app_name = app_label
                    test_module = get_test_module(app_name)

                    parts = test_label[len(app_name) + 1:].split('.')
                    test_module_name = parts[0]
                    new_suite = build_suite(get_app(app_name.split('.')[-1]))
                    if is_custom_test_package(test_module) and not \
                                                        suite.countTestCases():
                        test_module = import_module('.'.join([
                                        app_name, 'tests', test_module_name]))

                        parts_num = len(parts)
                        if parts_num == 1:
                            new_suite = defaultTestLoader.loadTestsFromModule(
                                                                test_module)
                        if parts_num == 2:
                            new_suite = defaultTestLoader.loadTestsFromName(
                                                        parts[1], test_module)
                        elif parts_num == 3:
                            klass = getattr(test_module, parts[1])
                            new_suite = klass(parts[2])

                    suite.addTest(new_suite)
                else:
                    for test_suite in self.load_from_app(test_label):
                        suite.addTest(test_suite)
        else:
            for app in self.get_apps():
                for test_suite in self.load_from_app(app):
                    suite.addTest(test_suite)

        if extra_tests:
            for test in extra_tests:
                suite.addTest(test)

        return reorder_suite(suite, (TestCase,))

if 'django_jenkins' in settings.INSTALLED_APPS:
    from django_jenkins.runner import CITestSuiteRunner

    class JenkinsDiscoveryDjangoTestSuiteRunner(DiscoveryDjangoTestSuiteRunner,
                                                CITestSuiteRunner):
        ''' The same as DiscoveryDjangoTestSuiteRunner but for jenkins '''
