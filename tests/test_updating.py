# -*- coding: utf-8 -*-

import urllib.parse
import responses
from flask_cheddargetter import Plan
from flask_cheddargetter import Customer
from flask_cheddargetter import Subscription
from flask_cheddargetter.exceptions import ValidationError

from . import TestBase


class UpdatingTests(TestBase):
    @responses.activate
    def test_create_customer_without_subscription(self):
        responses.add(
            responses.POST,
            Customer.build_url("/customers/new", is_new=True),
            status=200,
            body="<xml></xml>",
            content_type="application/xml",
        )

        customer = Customer()
        customer.code = 1
        customer.first_name = "Test"
        customer.last_name = "User"
        customer.email = "Email"
        customer.update_metadata("address", "123 Test street")
        customer.save()

        request = responses.calls[0].request

        assert request.method == "POST"

        body = urllib.parse.parse_qs(request.body)

        assert body["code"] == ["1"]
        assert body["firstName"] == ["Test"]
        assert body["lastName"] == ["User"]
        assert body["email"] == ["Email"]
        assert body["metaData[address]"] == ["123 Test street"]

    @responses.activate
    def test_create_customer_with_subscription(self):
        responses.add(
            responses.POST,
            Customer.build_url("/customers/new", is_new=True),
            status=200,
            body="<xml></xml>",
            content_type="application/xml",
        )
        responses.add(
            responses.POST,
            Plan.build_url("/plans/get", code="FREE_MONTHLY"),
            body=self.read_fixture("plan_free_monthly.xml"),
            content_type="application/xml",
        )

        customer = Customer()
        customer.code = "1"
        customer.first_name = "Test"
        customer.last_name = "User"
        customer.email = "Email"
        customer.subscription.plan_code = "FREE_MONTHLY"
        customer.subscription.cc_number = "1234123412341234"
        customer.subscription.cc_first_name = "First"
        customer.subscription.cc_last_name = "Last"
        customer.subscription.cc_expiration = "20/2020"
        customer.subscription.cc_card_code = "123"
        customer.save()

        # There should be 2 calls, one to fetch the plan information then one
        # to create the customer with the subscription
        assert len(responses.calls) == 2
        assert responses.calls[0].request.method == "POST"
        request = responses.calls[1].request
        assert request.method == "POST"

        body = urllib.parse.parse_qs(request.body)

        assert body["code"] == ["1"]
        assert body["firstName"] == ["Test"]
        assert body["lastName"] == ["User"]
        assert body["email"] == ["Email"]
        assert body["subscription[planCode]"] == ["FREE_MONTHLY"]
        assert body["subscription[ccNumber]"] == ["1234123412341234"]
        assert body["subscription[ccFirstName]"] == ["First"]
        assert body["subscription[ccLastName]"] == ["Last"]
        assert body["subscription[ccExpiration]"] == ["20/2020"]
        assert body["subscription[ccCardCode]"] == ["123"]

        # This should not result in an additional call because nothing has been
        # changed since the last save
        customer.save()
        assert len(responses.calls) == 2

    @responses.activate
    def test_update_customer(self):
        # Response for customer query
        responses.add(
            responses.POST,
            Customer.build_url("/customers/get"),
            body=self.read_fixture("customers_without_items.xml"),
            content_type="application/xml",
        )

        customers = Customer.all()
        assert len(customers) == 1
        customer = customers[0]

        # Response for edit request
        responses.add(
            responses.POST,
            Customer.build_url("/customers/edit", code=customer.code),
            status=200,
            body="<xml></xml>",
            content_type="application/xml",
        )

        # Nothing to update yet
        customer.save()
        assert len(responses.calls) == 1

        # Still nothing to save
        customer.first_name = getattr(customer, "first_name")
        customer.last_name = getattr(customer, "last_name")
        customer.save()
        assert len(responses.calls) == 1

        # Really saving something this time
        customer.first_name = "New first name"
        customer.last_name = "New last name"
        customer.update_metadata("key_2", "value_9")
        customer.update_metadata("key_3", "value_3")
        customer.save()
        request = responses.calls[1].request
        assert request.method == "POST"
        body = urllib.parse.parse_qs(request.body)
        assert body["firstName"] == ["New first name"]
        assert body["lastName"] == ["New last name"]
        assert body["metaData[key_2]"] == ["value_9"]
        assert body["metaData[key_3]"] == ["value_3"]

    @responses.activate
    def test_update_customer_subscription(self):
        # Response for customer query
        responses.add(
            responses.POST,
            Customer.build_url("/customers/get"),
            body=self.read_fixture("customers_without_items.xml"),
            content_type="application/xml",
        )
        # Response for query to new plan when plan code for subscription is
        # changed
        responses.add(
            responses.POST,
            Plan.build_url("/plans/get", code="PAID_MONTHLY"),
            body=self.read_fixture("plan_paid_monthly.xml"),
            content_type="application/xml",
        )

        customers = Customer.all()
        assert len(customers) == 1
        customer = customers[0]

        # Response for edit request
        responses.add(
            responses.POST,
            Customer.build_url("/customers/edit", code=customer.code),
            status=200,
            body="<xml></xml>",
            content_type="application/xml",
        )

        customer.subscription.plan_code = "PAID_MONTHLY"
        customer.save()

        assert len(responses.calls) == 3

        edit_request = responses.calls[2].request
        body = urllib.parse.parse_qs(edit_request.body)

        assert body["subscription[planCode]"] == ["PAID_MONTHLY"]
