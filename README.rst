====================
Django Test Tools
====================

The Django Test Tools is a set of utilities and tools to make django tests
faster and easier to maintain. Currently application provide test runner
with persistent database. The test database would be automatically sync'ed and
migrated along with main database.


Installation
============

#. Add the `test_tools` directory to your Python path.

#. Add `test_tools` to your `INSTALLED_APPS` setting so Django can find the
   signals.

#. Set test runner. You can use jenkins test runner as well but django_jenkins 
   should be in your INSTALLED_APPS::

    TEST_RUNNER = 'test_tools.test_runner.DiscoveryDjangoTestSuiteRunner'
    JENKINS_TEST_RUNNER = 'test_tools.test_runner.JenkinsDiscoveryDjangoTestSuiteRunner'
    
#. Create test database so application can sync it and probably migrate. Name 
   for test database can be set in DATABASES as TEST_NAME. If TEST_NAME
   is not provided the `test_` prefix would be added to regular database NAME.



Utils
=================

#. `test_tools.utils.model_factory`: Factory for creating objects in place 
    since fixtures may be slow and hard to maintain sometimes. The basic usage::

        user = model_factory(User, username='john')

    Factory will return NOT saved user object by default. To make an actual insert
    save=True should be passed as following::

        user = model_factory(User, username='john', save=True)

    There is a possibility to create a bunch of objects::

        user = model_factory(User, username=['john', 'tom'], last_name=['Smith', 'Green'], save=True)

    The length of every list should be equal.


#. `test_tools.utils.get_fake_email`: Simply return one or more fake emails::

        get_fake_email() 
        # this will return 'email_0@example.com'
        get_fake_email(2) 
        # this will return ['email_0@example.com', 'email_1@example.com']


#. `test_tools.utils.site_required`: This decorator simply creates a Site 
    object before decorated test or test case runs.


#. `test_tools.utils.no_database`: Decorator which replace django's cursor 
    with mock object and raise an error if test trying to access database. 
    Wrap your test with @no_database if you are sure that test shouldn't access database.


#. `test_tools.utils.profile`: Decorator which writes a profiling log with 
    hotshot module. You can specify the folder by PROFILE_LOG_BASE in settings.py. 
    It is set to /tmp by default::

        @profile('my_test.prof')
        def test_something(self):
            pass
    
    Then you can read the log by something like::
    
        stats = hotshot.stats.load('/tmp/my_test.prof')
        stats.strip_dirs()
        stats.sort_stats('time')
        stats.print_stats(10)



TODOs and BUGS
=================
Feel free to submit those: https://github.com/plus500s/django-test-tools/issues