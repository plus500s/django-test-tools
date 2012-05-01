from setuptools import setup, find_packages

setup(
    name='django-test-tools',
    version='0.1',
    description='Set of utils and tools for improving testing with django',
    long_description=open('README.rst').read(),
    # Get more strings from http://www.python.org/pypi?:action=list_classifiers
    author='Andrey Zarubin',
    author_email='andrey@anvil8.com',
    url='https://github.com/django-debug-toolbar/django-debug-toolbar',
    download_url='https://github.com/django-debug-toolbar/django-debug-toolbar/downloads',
    license='BSD',
    packages=find_packages(exclude=('tests', 'example')),
    install_requires=[
        'django>=1.1,<1.5',
        'mock>=0.8.0',
    ],
    test_suite='runtests.runtests',
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        'Development Status :: 1 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)