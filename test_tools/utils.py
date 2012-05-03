''' Utility functions for tests '''

import mock
import hotshot
import os

from hashlib import sha1
from functools import wraps
from django.contrib.auth.models import User
from django.test import Client
from django.utils.datastructures import SortedDict
from django.contrib.sites.models import Site
from django.conf import settings

try:
    PROFILE_LOG_BASE = settings.PROFILE_LOG_BASE
except AttributeError:
    PROFILE_LOG_BASE = "/tmp"


class DebugList(list):
    '''
    Extended list that provide diff functionality for model objects
    '''
    fields = None

    def __init__(self, *args, **kwargs):
        ''' Intialize tracked fields '''
        self.fields = kwargs.pop('fields', None)
        super(DebugList, self).__init__(*args, **kwargs)

    def get_order_diff(self, objects, message):
        ''' Build wrong order message '''
        convert_to_id = lambda obj: obj.id
        actual_ids = map(convert_to_id, objects)
        expected_ids = map(convert_to_id, self)
        diff = reason = ''
        if actual_ids != expected_ids and set(actual_ids) == set(expected_ids):
            reason = "Wrong ID order"
            diff = "Expect: {0}\nGot:    {1}".format(
                ' '.join(map(str, actual_ids)),
                ' '.join(map(str, expected_ids)))
            msg = message.format(reason, diff)
            return msg

    def get_diff(self, objects, ordered=False):
        ''' Build a diff message '''
        if not isinstance(objects, list):
            objects = list(objects)
        message = "{0}\n{1}"
        reason = None
        diff = ''
        if len(self) != len(objects):
            reason = "Expected length: {0} but got {1} objects".format(
                                                    len(self), len(objects))
        elif ordered:
            msg = self.get_order_diff(objects, message)
            if msg is not None:
                return msg

        map_objects = lambda obj_list: {obj.id: obj for obj in obj_list}
        missed_objects = filter(lambda obj: not obj.id in map_objects(objects),
                                                                        self)
        extra_objects = filter(lambda obj: not obj.id in map_objects(self),
                                                                    objects)

        def build_diff(obj_list):
            ''' Create text message for object '''
            result = []
            for obj in obj_list:
                fields = {}
                for field_name in self.fields:
                    fields[field_name] = getattr(obj, field_name)
                fields = map(lambda key_value: '{0}={1}'.format(*key_value),
                    fields.items())
                result.append('{0}({1})'.format(obj.__class__.__name__,
                                                ', '.join(fields)))
            return result

        if not reason and (missed_objects or extra_objects):
            reason = "Expected and actual objects are different"

        if missed_objects:
            diff = "Missed objects: \n{0}".format(
                                    "\n".join(build_diff(missed_objects)))

        if extra_objects:
            diff += "\n\nExtra objects: \n{0}".format(
                                        "\n".join(build_diff(extra_objects)))

        return message.format(reason, diff)

    def has_diff(self, objects, ordered=False):
        ''' Return true if all the objects has the same ids as in self '''
        actual_ids = map(lambda obj: obj.id, objects)
        expected_ids = map(lambda obj: obj.id, self)
        if len(actual_ids) != len(expected_ids):
            return True
        if ordered:
            return actual_ids != expected_ids
        return set(actual_ids) != set(expected_ids)


def model_factory(model, *args, **kwargs):
    ''' Simple object fabric for tests '''
    save = kwargs.pop('save', False)
    kwargs = SortedDict(kwargs)
    if kwargs and not isinstance(kwargs.values()[0], list):
        for key in kwargs:
            kwargs[key] = [kwargs[key]]

    def _create_model_obj(**_kwargs):
        ''' Create or build object '''
        if save:
            return model.objects.create(*args, **_kwargs)
        return model(*args, **_kwargs)

    models = DebugList(fields=kwargs.keys())
    if kwargs:
        model_kwargs = map(lambda value: dict(zip(kwargs.keys(), value)),
                       zip(*kwargs.values()))
        for model_kw in model_kwargs:
            models.append(_create_model_obj(**model_kw))
    else:
        models.append(_create_model_obj())

    if len(models) == 1:
        return models[0]
    return models


def get_logged_in_client():
    user = model_factory(User, email=get_fake_email())
    user.set_password('password')
    user.save()
    client = Client()
    client.login(username=get_fake_email(), password='password')
    return client


def get_form(forms, fields):
    '''
    Simply iterate over forms and return first occurred with
    required fields
    '''
    for form in forms.values():
        required_present = True
        for field in fields:
            required_present &= (field in form.fields)
        if required_present:
            return form
    raise AttributeError('Form with fields {0} does not exist'.format(
                                                        ', '.join(fields)))


def site_required(func):
    ''' Simply creates a Site from settings '''
    @wraps(func)
    def _wrapper(*args, **kwargs):
        ''' Create a Site before call a test function '''
        model_factory(Site, id=settings.SITE_ID, save=True)
        return func(*args, **kwargs)

    return _wrapper


def no_database(func):
    ''' Raises exception if database hit performed '''
    @wraps(func)
    def wrapped_func(*args, **kwargs):
        ''' Execute original function in no database context '''
        cursor_wrapper = mock.Mock()
        cursor_wrapper.side_effect = \
            RuntimeError("No touching the database!")
        with mock.patch("django.db.backends.util.CursorWrapper",
                        cursor_wrapper):
            func(*args, **kwargs)

    return wrapped_func


def get_fake_email(num=1):
    ''' Always returns fake email '''
    emails = []
    for counter in range(num):
        emails.append('email_{0}@example.com'.format(counter))
    if len(emails) == 1:
        return emails[0]
    return emails


def get_sha1():
    ''' Return always the same valid sha1 hash '''
    return sha1('some key').hexdigest()


def profile(log_file):
    """Profile some callable.

    This decorator uses the hotshot profiler to profile some callable (like
    a view function or method) and dumps the profile data somewhere sensible
    for later processing and examination.

    It takes one argument, the profile log name. If it's a relative path, it
    places it under the PROFILE_LOG_BASE. It also inserts a time stamp into the
    file name, such that 'my_view.prof' become 'my_view-20100211T170321.prof',
    where the time stamp is in UTC. This makes it easy to run and compare
    multiple trials.
    """

    if not os.path.isabs(log_file):
        log_file = os.path.join(PROFILE_LOG_BASE, log_file)

    def _outer(f):
        def _inner(*args, **kwargs):
            # Add a timestamp to the profile output when the callable
            # is actually called.
            (base, ext) = os.path.splitext(log_file)
            final_log_file = base + ext
            try:
                os.unlink(final_log_file)
            except OSError:
                pass
            prof = hotshot.Profile(final_log_file)
            try:
                ret = prof.runcall(f, *args, **kwargs)
            finally:
                prof.close()
            return ret

        return _inner
    return _outer
