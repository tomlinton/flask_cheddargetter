# -*- coding: utf-8 -*-

import os
import unittest
import flask


class TestBase(unittest.TestCase):

    def read_fixture(self, filename):
        path = os.path.join(os.path.dirname(__file__), 'fixtures', filename)
        f = open(path)
        return f.read()

    def setUp(self):
        self.app = flask.Flask(__name__)
        self.app.config['CHEDDAR_API_URL'] = 'https://127.0.0.1'
        self.app.config['CHEDDAR_PRODUCT'] = 'Test'
        self.app.config['CHEDDAR_EMAIL'] = 'Test'
        self.app.config['CHEDDAR_PASSWORD'] = 'Test'
        self.app.config['TESTING'] = True
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        pass

