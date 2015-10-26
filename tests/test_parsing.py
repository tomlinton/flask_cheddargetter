# -*- coding: utf-8 -*-

import os
import arrow
import responses
from lxml import etree

from flask_cheddargetter import CheddarObject
from flask_cheddargetter import Customer
from flask_cheddargetter import Plan
from flask_cheddargetter import GatewayAccount
from flask_cheddargetter.exceptions import BadRequest
from flask_cheddargetter.exceptions import NotFound

from . import TestBase


class ParsingTests(TestBase):

    def read_fixture(self, filename):
        path = os.path.join(os.path.dirname(__file__), 'fixtures', filename)
        f = open(path)
        return f.read()

    @responses.activate
    def test_error_no_customer_parsing(self):
        responses.add(responses.POST,
                      Customer.build_url('/customers/get', code=-1),
                      status=404,
                      body=self.read_fixture('error_no_customer.xml'),
                      content_type='application/xml')

        with self.assertRaises(NotFound) as context:
            customer = Customer.get(-1)

        assert context.exception.error_id == '73542'
        assert context.exception.code == '404'
        assert context.exception.message == 'Customer not found'
        assert context.exception.aux_code == ''

    @responses.activate
    def test_error_no_product_parsing(self):
        responses.add(responses.POST,
                      Customer.build_url('/customers/get'),
                      status=400,
                      body=self.read_fixture('error_no_product.xml'),
                      content_type='application/xml')

        with self.assertRaises(BadRequest) as context:
            customers = Customer.all()

        assert context.exception.error_id == '149947'
        assert context.exception.code == '400'
        assert context.exception.message == 'No product selected. Need a ' \
                'productId or productCode.'
        assert context.exception.aux_code == ''

    @responses.activate
    def test_plans_parsing(self):
        responses.add(responses.POST, Plan.build_url('/plans/get'),
                      body=self.read_fixture('plans.xml'),
                      content_type='application/xml')

        plans = Plan.all()

        assert len(plans) == 2
        plan = plans[0]
        assert plan.id == '6b0d13f4-6bef-102e-b098-40402145ee8b'
        assert plan.code == 'FREE_MONTHLY'
        assert plan.recurring_charge_amount == 0.0
        assert plan.name == 'Free Monthly'
        assert plan.billing_frequency == 'monthly'
        assert plan.billing_frequency_quantity == 1
        assert plan.setup_charge_code == None
        assert plan.is_active == 1
        assert plan.is_free == 1
        assert plan.billing_frequency_unit == 'months'
        assert plan.initial_bill_count_unit == 'months'
        assert plan.setup_charge_amount == 0.0
        assert plan.billing_frequency_per == 'month'
        assert plan.trial_days == 0
        assert plan.created_datetime == \
                arrow.get('2011-01-07T20:46:43+00:00').datetime
        assert plan.recurring_charge_code == 'FREE_MONTHLY_RECURRING'
        assert plan.initial_bill_count == 1
        assert plan.description == 'A free monthly plan'

        plan = plans[1]
        assert plan.id == '11af9cfc-6bf2-102e-b098-40402145ee8b'
        assert plan.code == 'PAID_MONTHLY'
        assert plan.recurring_charge_amount == 20.0
        assert plan.name == 'Paid Monthly'
        assert plan.billing_frequency == 'monthly'
        assert plan.billing_frequency_quantity == 1
        assert plan.setup_charge_code == None
        assert plan.is_active == 1
        assert plan.is_free == 0
        assert plan.billing_frequency_unit == 'months'
        assert plan.initial_bill_count_unit == 'months'
        assert plan.setup_charge_amount == 0.0
        assert plan.billing_frequency_per == 'month'
        assert plan.trial_days == 0
        assert plan.created_datetime == \
                arrow.get('2011-01-07T21:05:42+00:00').datetime
        assert plan.recurring_charge_code == 'PAID_MONTHLY_RECURRING'
        assert plan.initial_bill_count == 1
        assert plan.description == None

    @responses.activate
    def test_plan_with_items_parsing(self):
        responses.add(responses.POST, Plan.build_url('/plans/get'),
                      body=self.read_fixture('plans_with_items.xml'),
                      content_type='application/xml')

        plans = Plan.all()

        assert len(plans) == 3
        plan = plans[0]
        assert plan.id == '6b0d13f4-6bef-102e-b098-40402145ee8b'
        assert plan.code == 'FREE_MONTHLY'
        assert plan.recurring_charge_amount == 0.0
        assert plan.name == 'Free Monthly'
        assert plan.billing_frequency == 'monthly'
        assert plan.billing_frequency_quantity == 1
        assert plan.setup_charge_code == None
        assert plan.is_active == 1
        assert plan.is_free == 1
        assert plan.billing_frequency_unit == 'months'
        assert plan.initial_bill_count_unit == 'months'
        assert plan.setup_charge_amount == 0.0
        assert plan.billing_frequency_per == 'month'
        assert plan.trial_days == 0
        assert plan.created_datetime == \
                arrow.get('2011-01-07T20:46:43+00:00').datetime
        assert plan.recurring_charge_code == 'FREE_MONTHLY_RECURRING'
        assert plan.initial_bill_count == 1
        assert plan.description == 'A free monthly plan'
        item = plan.items[0]
        assert item.id == 'd19b4970-6e5a-102e-b098-40402145ee8b'
        assert item.code == 'MONTHLY_ITEM'
        assert item.quantity_included == 0
        assert item.is_periodic == 0
        assert item.overage_amount == 0.00
        assert item.created_datetime == \
                arrow.get('2011-01-10T22:40:34+00:00').datetime
        item = plan.items[1]
        assert item.id == 'd19ef2f0-6e5a-102e-b098-40402145ee8b'
        assert item.code == 'ONCE_ITEM'
        assert item.quantity_included == 0
        assert item.is_periodic == 0
        assert item.overage_amount == 0.00
        assert item.created_datetime == \
                arrow.get('2011-01-10T22:40:34+00:00').datetime

        plan = plans[1]
        assert plan.id == 'd19974a6-6e5a-102e-b098-40402145ee8b'
        assert plan.code == 'TRACKED_MONTHLY'
        assert plan.recurring_charge_amount == 10.0
        assert plan.name == 'Tracked Monthly'
        assert plan.billing_frequency == 'monthly'
        assert plan.billing_frequency_quantity == 1
        assert plan.setup_charge_code == None
        assert plan.is_active == 1
        assert plan.is_free == 0
        assert plan.billing_frequency_unit == 'months'
        assert plan.initial_bill_count_unit == 'months'
        assert plan.setup_charge_amount == 0.0
        assert plan.billing_frequency_per == 'month'
        assert plan.trial_days == 0
        assert plan.created_datetime == \
                arrow.get('2011-01-10T22:40:34+00:00').datetime
        assert plan.recurring_charge_code == 'TRACKED_MONTHLY_RECURRING'
        assert plan.initial_bill_count == 1
        assert plan.description == None
        assert len(plan.items) == 2
        item = plan.items[0]
        assert item.id == 'd19b4970-6e5a-102e-b098-40402145ee8b'
        assert item.code == 'MONTHLY_ITEM'
        assert item.quantity_included == 2
        assert item.is_periodic == 1
        assert item.overage_amount == 10.00
        assert item.created_datetime == \
                arrow.get('2011-01-10T22:40:34+00:00').datetime
        item = plan.items[1]
        assert item.id == 'd19ef2f0-6e5a-102e-b098-40402145ee8b'
        assert item.code == 'ONCE_ITEM'
        assert item.quantity_included == 0
        assert item.is_periodic == 0
        assert item.overage_amount == 10.00
        assert item.created_datetime == \
                arrow.get('2011-01-10T22:40:34+00:00').datetime

        plan = plans[2]
        assert plan.id == '11af9cfc-6bf2-102e-b098-40402145ee8b'
        assert plan.code == 'PAID_MONTHLY'
        assert plan.recurring_charge_amount == 20.0
        assert plan.name == 'Paid Monthly'
        assert plan.billing_frequency == 'monthly'
        assert plan.billing_frequency_quantity == 1
        assert plan.setup_charge_code == None
        assert plan.is_active == 1
        assert plan.is_free == 0
        assert plan.billing_frequency_unit == 'months'
        assert plan.initial_bill_count_unit == 'months'
        assert plan.setup_charge_amount == 0.0
        assert plan.billing_frequency_per == 'month'
        assert plan.trial_days == 0
        assert plan.created_datetime == \
                arrow.get('2011-01-07T21:05:42+00:00').datetime
        assert plan.recurring_charge_code == 'PAID_MONTHLY_RECURRING'
        assert plan.initial_bill_count == 1
        assert plan.description == None
        assert len(plan.items) == 2
        item = plan.items[0]
        assert item.id == 'd19b4970-6e5a-102e-b098-40402145ee8b'
        assert item.code == 'MONTHLY_ITEM'
        assert item.quantity_included == 0
        assert item.is_periodic == 0
        assert item.overage_amount == 0.00
        assert item.created_datetime == \
                arrow.get('2011-01-10T22:40:34+00:00').datetime
        item = plan.items[1]
        assert item.id == 'd19ef2f0-6e5a-102e-b098-40402145ee8b'
        assert item.code == 'ONCE_ITEM'
        assert item.quantity_included == 0
        assert item.is_periodic == 0
        assert item.overage_amount == 0.00
        assert item.created_datetime == \
                arrow.get('2011-01-10T22:40:34+00:00').datetime

    @responses.activate
    def test_customer_without_items_parsing(self):
        #: Mock plans response
        responses.add(responses.POST, Customer.build_url('/customers/get'),
                      body=self.read_fixture('customers_without_items.xml'),
                      content_type='application/xml')

        customers = Customer.all()

        assert len(customers) == 1

        customer = customers[0]
        assert type(customer) == Customer

        assert customer._to_persist == {}
        assert customer._product_code == 'Test'

        #: Customer data
        assert customer.id == '10681b62-6dcd-102e-b098-40402145ee8b'
        assert customer.first_name == 'Test'
        assert customer.last_name == 'User'
        assert customer.email == 'garbage@saaspire.com'
        assert customer.vat_number == None
        assert customer.is_vat_exempt == 0
        assert customer.company == None
        assert customer.gateway_token == None
        assert customer.modified_datetime == \
                arrow.get('2011-01-10T05:45:51+00:00').datetime
        assert customer.created_datetime == \
                arrow.get('2011-01-10T05:45:51+00:00').datetime
        assert customer.referer == None
        assert customer.referer_host == None
        assert customer.notes == None
        #: TODO fix metadata implementation
        #: assert customer.metadata == []

        #: Campaign data
        assert customer.campaign_name == None
        assert customer.campaign_medium == None
        assert customer.campaign_source == None
        assert customer.campaign_content == None
        assert customer.campaign_term == None
        assert customer.first_contact_datetime == None

        #: Verify subscription
        assert len(customer.subscriptions) == 1
        #: Check that subscription property correctly points to the current
        #: subscription
        assert customer.subscription == customer.subscriptions[0]
        subscription = customer.subscription
        #: Check that parent customer is set correctly
        assert subscription.customer == customer
        assert subscription._to_persist == {}
        assert subscription._product_code == 'Test'

        assert subscription.id == '106953e3-6dcd-102e-b098-40402145ee8b'
        assert subscription.cc_last_four == None
        assert subscription.cc_company == None
        assert subscription.cc_state == None
        assert subscription.created_datetime == \
                arrow.get('2011-01-10T05:45:51+00:00').datetime
        assert subscription.canceled_datetime == None
        assert subscription.cc_type == None
        assert subscription.cc_city == None
        assert subscription.cc_zip == None
        assert subscription.cc_address == None
        assert subscription.cc_country == None
        assert subscription.cc_first_name == None
        assert subscription.cc_last_name == None
        assert subscription.cc_expiration_date == None
        assert subscription.gateway_token == None

        assert type(subscription.gateway_account) == GatewayAccount
        #: TODO fix handling of id
        #: assert subscription.gateway_account.id == \
        #:         'f3fb7029-11f4-475f-ab8d-80f8771e26d0'
        assert subscription.gateway_account.type == 'paypal'
        assert subscription.gateway_account.gateway == 'PayPal'
        assert subscription.gateway_account.subscription == subscription

        #: Verify subscription plan
        assert len(subscription.plans) == 1
        assert subscription.plan == subscription.plans[0]
        plan = subscription.plan
        #: Check parent subscription is set correctly
        assert plan.subscription == subscription

        assert plan._to_persist == {}
        assert plan._product_code == 'Test'

        assert plan.code == 'FREE_MONTHLY'
        assert plan.id == '6b0d13f4-6bef-102e-b098-40402145ee8b'
        assert plan.recurring_charge_amount == 0.0
        assert plan.name == 'Free Monthly'
        assert plan.billing_frequency == 'monthly'
        assert plan.setup_charge_code == None
        assert plan.is_active == 1
        assert plan.is_free == 1
        assert plan.billing_frequency_unit == 'months'
        assert plan.initial_bill_count_unit == 'months'
        assert plan.setup_charge_amount == 0.0
        assert plan.billing_frequency_per == 'month'
        assert plan.trial_days == 0
        assert plan.created_datetime == \
                arrow.get('2011-01-07T20:46:43+00:00').datetime
        assert plan.recurring_charge_code == 'FREE_MONTHLY_RECURRING'
        assert plan.initial_bill_count == 1
        assert plan.description == 'A free monthly plan'

        #: Verify subscription invoices
        assert len(subscription.invoices) == 1
        invoice = subscription.invoices[0]

        #: Check parent subscription is set correctly
        assert invoice.subscription == subscription

        assert invoice._to_persist == {}
        assert invoice._product_code == 'Test'

        assert invoice.id == '106ed222-6dcd-102e-b098-40402145ee8b'
        assert invoice.code == None
        assert invoice.paid_transaction_id == None
        assert invoice.created_datetime == \
                arrow.get('2011-01-10T05:45:51+00:00').datetime
        assert invoice.number == 1
        assert invoice.billing_datetime == \
                arrow.get('2011-02-10T05:45:51+00:00').datetime
        assert invoice.vat_rate == None
        assert invoice.type == 'subscription'
        assert invoice.charges == []

