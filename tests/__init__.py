# -*- coding: utf-8 -*-

import unittest
import flask


class TestBase(unittest.TestCase):

    def setUp(self):
        self.app = flask.Flask(__name__)
        self.app.config['CHEDDAR_API_URL'] = 'https://127.0.0.1'
        self.app.config['CHEDDAR_PRODUCT'] = 'Test'
        self.app.config['TESTING'] = True
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        pass

