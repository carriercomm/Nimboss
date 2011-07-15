#!/usr/bin/env python

setupdict = {
    'name' : 'nimboss',
    'version' : '0.4.4',
    'description' : 'Nimbus cloud client API',
    'url': 'http://github.com/nimbusproject/Nimboss',
    'download_url' : 'http://ooici.net/packages',
    'license' : 'Apache 2.0',
    'author' : 'David LaBissoniere',
    'author_email' : 'labisso@mcs.anl.gov',
    'keywords': ['nimbus','ooci'],
    'classifiers' : [
    'Development Status :: 3 - Alpha',
    'Environment :: Console',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: Apache Software License',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Topic :: Scientific/Engineering'],
}

try:
    from setuptools import setup, find_packages
    setupdict['packages'] = find_packages()
    setupdict['test_suite'] = 'nimboss.test'
    setupdict['install_requires'] = ['apache-libcloud', 'httplib2', 'simplejson']
    setupdict['include_package_data'] = True
    setup(**setupdict)

except ImportError:
    from distutils.core import setup
    setupdict['packages'] = ['nimboss']
    setup(**setupdict)
