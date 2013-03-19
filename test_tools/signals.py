''' Syncing and migrating test database '''

from django.db.models.signals import post_syncdb
from django.dispatch import receiver
from django.core.management import call_command
from test_tools.test_runner import get_test_db_name
from django.db import connections
from django.conf import settings


def reset_connection(connection, new_name):
    ''' Change database name '''
    connection.close()
    connection.settings_dict["NAME"] = new_name
    connection.features.confirm()
    connection.cursor()


def call_test_db_command(command):
    ''' Call command on test database '''
    for alias in connections:
        connection = connections[alias]
        old_name = connection.settings_dict["NAME"]
        test_db_name = get_test_db_name(connection)
        if not old_name.startswith('test_'):
            reset_connection(connection, test_db_name)
            call_command(command,
                interactive=False,
                database=connection.alias,
                load_initial_data=False)
            reset_connection(connection, old_name)


@receiver(post_syncdb)
def sync_test_db(sender, **kwargs):
    ''' Syncing test database '''
    app_label = '.'.join(sender.__name__.split('.')[:-1])
    if app_label == settings.INSTALLED_APPS[-1]:
        call_test_db_command('syncdb')


if 'south' in settings.INSTALLED_APPS:
    from south.signals import post_migrate

    @receiver(post_migrate)
    def migrate_test_db(sender, **kwargs):
        ''' Migrate test db '''
        call_test_db_command('migrate')
