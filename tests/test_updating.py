# -*- coding: utf-8 -*-

from flask_cheddargetter import Customer
from flask_cheddargetter import Subscription
from flask_cheddargetter.exceptions import ValidationError

from . import TestBase


class UpdatingTests(TestBase):

    def test_create_customer_without_subscription(self):
        customer = Customer()
        customer.code = 1
        customer.first_name = 'Test'
        customer.last_name = 'User'
        customer.email = 'Email'

        assert 'first_name' in customer._to_persist
        assert 'last_name' in customer._to_persist
        assert 'email' in customer._to_persist

    def test_create_customer_with_subscription(self):
        pass

    def test_create_customer_without_subscription_required_fields(self):
        customer = Customer()
        customer.code = 1
        customer.first_name = 'Test'
        customer.last_name = 'User'

        with self.assertRaises(ValidationError):
            customer.validate()

    def test_create_customer_with_subscription_required_fields(self):
        pass

    def test_update_customer(self):
        pass

    def test_update_customer_subscription(self):
        pass

