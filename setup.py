# -*- coding: utf-8 -*-

from distutils.core import setup


setup(name='flask_cheddargetter',
      version='0.1.0',
      description='A Flask extension for integrating subscriptions via'
                  'CheddarGetter (http://cheddargetter.com).',
      author='Thomas Linton',
      author_email='tlinton@fastmail.fm',
      packages=['flask_cheddargetter'],
      requires=['arrow', 'lxml', 'requests', 'inflection', 'simplejson']
)

