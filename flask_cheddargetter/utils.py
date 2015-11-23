# -*- coding: utf-8 -*-

from flask_cheddargetter import Customer
from flask_cheddargetter import Plan


def get_items_by_customer_code():
    """Helper method that uses the /customer/list API of endpoint to get a
    dictionary of the items available to each customer keyed by code. This
    is useful if you need to do a daily task for each customer and you need
    to know the features available to them, but you don't want to make a single
    query to CheddarGetter for each customer."""

    plans = {plan.code: plan for plan in Plan.all()}
    customers = Customer.list()

    items = {}
    for customer in customers:
        # Grab the items for each customer from the plan of the subscription
        items[int(customer.code)] = {item.name: item.quantity_included \
                for item in plans[customer.subscription.plan.code].items}

    return items


