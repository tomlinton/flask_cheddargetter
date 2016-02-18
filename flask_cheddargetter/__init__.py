# -*- coding: utf-8 -*-

"""
This is an extension for Flask to integrate CheddarGetter for subscription
management. It is heavily inspired by pycheddar:

    https://github.com/feedmagnet/pycheddar

"""

import re
import sys
import copy
import arrow
import requests
import datetime
import inflection
import simplejson as json
from requests.adapters import HTTPAdapter
from os import environ
from lxml import etree
from flask import request
from flask import current_app

from .exceptions import BadRequest
from .exceptions import NotFound
from .exceptions import UnexpectedResponse
from .exceptions import GatewayFailure
from .exceptions import GatewayConnectionError
from .exceptions import ValidationError


try:
    from flask import _app_ctx_stack as stack
except ImportError:
    from flask import _request_ctx_stack as stack


class CheddarGetter(object):

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.config.setdefault('CHEDDAR_EMAIL',
                              environ.get('CHEDDAR_EMAIL', None))
        app.config.setdefault('CHEDDAR_PASSWORD',
                              environ.get('CHEDDAR_PASSWORD', None))
        app.config.setdefault('CHEDDAR_PRODUCT',
                              environ.get('CHEDDAR_PRODUCT', None))
        app.config.setdefault('CHEDDAR_MARKETING_COOKIE_NAME',
                              environ.get('CHEDDAR_MARKETING_COOKIE_NAME',
                                          None))

        if not hasattr(app, 'extensions'):
            app.extensions = {}
        app.extensions['cheddargetter'] = self

        self.cookie_name = app.config['CHEDDAR_MARKETING_COOKIE_NAME']
        return app

    def build_marketing_cookie(self):
        if not self.cookie_name:
            return False

        utm_params = {
            'utm_term': 'campaignTerm',
            'utm_campaign': 'campaignName',
            'utm_source': 'campaignSource',
            'utm_medium': 'campaignMedium',
            'utm_content': 'campaignContent'
        }

        if not request.cookies.get(self.cookie_name):
            # Marketing cookie was not set, set it
            cookie = {}
            cookie['firstContactDatetime'] = datetime.datetime.now().isoformat()
            cookie['referer'] = request.environ.get('HTTP_REFERER', 'direct')
            for utm_param, cg_param in utm_params.items():
                cookie[cg_param] = request.environ.get(utm_param, None)
            return cookie

        elif request.cookies.get('__utmz', None):
            # We have a marketing cookie, refine with __utmz cookie
            cookie = json.loads(request.cookies.get(self.cookie_name))

            utmz_string = request.cookies.get('__utmz')
            parsed_utmz_string = utmz_string.split('.')
            # Something is wrong, give up
            if len(parsed_utmz_string) < 4:
                return
            # Rejoin when src or cct might have a dot i.e. utmscr=example.com
            parsed_utmz_string[4] = '.'.join(parsed_utmz_string[4:])

            #pylint: disable=W0612
            _domain_hash, _timestamp, _session_number, _campaign_number, \
                    campaign_data = parsed_utmz_string

            # Extract campaign data
            translations = {
                'utmcsr': 'campaignSource',
                'utmccn': 'campaignName',
                'utmcmd': 'campaignMedium',
                'utmctr': 'campaignTerm',
                'utmcct': 'campaignContent'
            }
            for params in campaign_data.split('|'):
                key, value = params.split('=')
                if key in translations:
                    cookie[translations[key]] = value

            # Override some fields if this is an AdWords lead
            if 'gclid=' in campaign_data:
                cookie['campaignSource'] = 'google'
                cookie['campaignMedium'] = 'ppc'

            return cookie


class CheddarObject(object):
    """ A base class for CheddarGetter objects. """

    def __init__(self, parent=None, **kwargs):
        self._product_code = current_app.config['CHEDDAR_PRODUCT']
        self._data = {}
        self._to_persist = {}
        self._id = None
        self._code = None

        if parent is not None:
            setattr(self, parent.__class__.__name__.lower(), parent)

        for i in kwargs:
            setattr(self, i, kwargs[i])

    def __setattr__(self, key, value):
        # If modifying a private attribute of the class then set it directly
        if key[0] == '_':
            self.__dict__[key] = value
        elif key == 'code':
            if self._id is None:
                self._code = value
            else:
                raise AttributeError('Saved CheddarGetter object codes '
                                     'are immutable')
        elif key == 'id':
            raise AttributeError('CheddarGetter ID is immutable')
        elif isinstance(value, CheddarObject) or isinstance(value, list):
            self.__dict__[key] = value
        else:
            # Add value to dictionary of attributes to save to CheddarGetter
            if inflection.underscore(key) not in self._data or \
                    self._data[inflection.underscore(key)] != value:
                self._to_persist[inflection.underscore(key)] = value
            self._data[inflection.underscore(key)] = value

    def __getattr__(self, key):
        if key in ['id', 'code']:
            return self.__dict__['_{}'.format(key)]
        elif key[0] == '_' or key in self.__dict__:
            return self.__dict__[key]
        elif key in self._to_persist:
            return self._to_persist[inflection.underscore(key)]
        elif key in self._data:
            return self._data[inflection.underscore(key)]
        else:
            raise AttributeError, 'Key {} does not exist'.format(key)

    def __eq__(self, other):
        return self._id == other._id and self._id is not None

    def __neq__(self, other):
        return not self.__eq__(other)

    def __contains__(self, key):
        if key == 'id' or key == '_id':
            return self._id is not None
        if key == 'code' or key == '_code':
            return self._code is not None
        return key in self._data

    def __iter__(self):
        return self.iteritems()

    def _asdict(self):
        data = {}
        for key in getattr(self, '__serialize__', []):
            if hasattr(self, key):
                data[key] = getattr(self, key)
        return data

    def is_new(self):
        return not 'id' in self

    def _load_from_xml(self, xml):
        self._id = xml.get('id')
        self._code = xml.get('code')

        for child in xml.getchildren():
            if len(child.getchildren()) > 0:
                # Determine if children are all of the same type, e.g. Items
                # has many Item children, or if the current child should be
                # instantiated as a class
                is_list = len(set([i.tag for i in child.getchildren()])) == 1
                if not is_list:
                    # Single object
                    try:
                        cls = getattr(sys.modules[__name__],
                                      inflection.camelize(child.tag))
                        setattr(self, inflection.underscore(child.tag),
                                cls.from_xml(child, parent=self))
                    except AttributeError:
                        # No class for this object, ignore it
                        pass
                    continue
                else:
                    setattr(self, inflection.underscore(child.tag), [])
                    for item_xml in child.getchildren():
                        try:
                            cls = getattr(sys.modules[__name__],
                                          inflection.camelize(item_xml.tag))
                            attr = getattr(self,
                                           inflection.underscore(child.tag))
                            attr.append(cls.from_xml(item_xml, parent=self))
                        except AttributeError:
                            # Give up, remaining items are all the same and
                            # there is no class for them
                            break
                    continue

            key = inflection.underscore(child.tag)
            value = child.text
            if value is not None:
                # Parse numeric types
                if re.match(r'^[\d]+$', value):
                    value = int(value)
                elif re.match(r'^[\d.]+$', value):
                    value = float(value)
                # Parse datetimes, use naive detection of key to avoid trying
                # to parse every field
                elif 'datetime' in key:
                    try:
                        value = arrow.get(value).datetime
                    except Exception:
                        pass
            self._data[key] = value

        # Reset dirty data because all data should now be clean
        self._to_persist = {}

    def _is_dirty(self):
        return len(self._to_persist) > 0

    @classmethod
    def from_xml(cls, xml, **kwargs):
        parent = kwargs.pop('parent', None)
        new = cls(parent=parent, **kwargs)
        new._load_from_xml(xml)
        return new

    @classmethod
    def build_url(cls, path, code=None, is_new=False):
        # Build the request URL
        url = 'https://cheddargetter.com/xml' + path + '/productCode/{}'
        url = url.format(current_app.config.get('CHEDDAR_PRODUCT'))
        if code is not None and not is_new:
            url += '/code/{}'.format(code)
        return url

    @classmethod
    def request(cls, path, code=None, is_new=False, **kwargs):

        if not current_app.config['CHEDDAR_EMAIL']:
            raise Exception('CHEDDAR_EMAIL not configured')
        if not current_app.config['CHEDDAR_PASSWORD']:
            raise Exception('CHEDDAR_PASSWORD not configured')
        if not current_app.config['CHEDDAR_PRODUCT']:
            raise Exception('CHEDDAR_PRODUCT not configured')

        url = cls.build_url(path, code, is_new)
        if is_new:
            kwargs['code'] = code

        # Set keys to Zend convention
        for key in copy.copy(kwargs):
            # Handle metaData keys separately to avoid camel casing user
            # defined name attribute
            if '_' in key and not key.startswith('metaData'):
                kwargs[inflection.camelize(key, False)] = kwargs[key]
                del kwargs[key]

        # Execute the request
        client = requests.Session()
        client.auth = (current_app.config.get('CHEDDAR_EMAIL'),
                       current_app.config.get('CHEDDAR_PASSWORD'))
        response = client.post(url, data=kwargs)

        try:
            content = etree.fromstring(response.content)
        except:
            raise UnexpectedResponse('CheddarGetter sent Invalid XML',
                                     response.content)

        code_exception_map = {
            400: BadRequest,
            404: NotFound,
            412: BadRequest,
            422: GatewayFailure,
            500: GatewayConnectionError
        }

        if response.status_code > 400 or content.tag == 'error':
            if response.status_code in code_exception_map:
                exception = code_exception_map[response.status_code]
            else:
                exception = UnexpectedResponse
            # If the customer didn't exist in CheddarGetter the error will be
            # the only thing returned. If the customer did exist the error
            # will be embedded in the customer object
            error = content if content.tag == 'error' else \
                    content.find('.//error')
            raise exception(error.get('id', None),
                            error.get('code', None),
                            error.text,
                            error.get('auxCode', None))

        return content


class Customer(CheddarObject):

    __serialize__ = [
        'id',
        'first_name',
        'last_name',
        'email'
    ]

    def __init__(self, **kwargs):
        # Add an empty subscription to the customer object because the
        # CheddarGetter API creates a customer and subscription at the same
        # time
        self.subscriptions = []
        self.subscriptions.append(Subscription(parent=self))
        self.meta_data = []
        super(Customer, self).__init__(**kwargs)

    @classmethod
    def all(cls):
        try:
            customers = []
            xml = cls.request('/customers/get')
            for customer_xml in xml.getiterator(tag='customer'):
                customers.append(Customer.from_xml(customer_xml))
            return customers
        except NotFound:
            return []

    @classmethod
    def list(cls):
        """The list method of the CheddarGetter API returns a summary of each
        customer rather than the complete history. This is useful because the
        get method often is too large and is returned incomplete."""
        try:
            customers = []
            xml = cls.request('/customers/list')
            for customer_xml in xml.getiterator(tag='customer'):
                customers.append(Customer.from_xml(customer_xml))
            return customers
        except NotFound:
            return []

    @classmethod
    def get(cls, code):
        xml = cls.request('/customers/get', code=code)
        for customer_xml in xml.getiterator(tag='customer'):
            return Customer.from_xml(customer_xml)

    @property
    def subscription(self):
        return self.subscriptions[0]

    def save(self):
        # Collect all the keys from the subscription and modify them to
        # CheddarGetter format for submission with the customer
        subscription_fields = [
            'cc_first_name',
            'cc_last_name',
            'cc_number',
            'cc_expiration',
            'cc_card_code',
            'cc_zip',
            'return_url',
            'cancel_url',
            'method',
            'plan_code'
        ]
        for key in subscription_fields:
            if key in self.subscription._to_persist:
                self._to_persist['subscription[%s]' % key] = \
                        getattr(self.subscription, key)

        for datum in self.meta_data:
            if 'value' in datum._to_persist:
                self._to_persist['metaData[%s]' % datum.name] = datum.value

        if not self._to_persist:
            return

        if self.is_new():
            # Object doesn't exist in Cheddargetter, create it
            xml = self.request('/customers/new', code=self._code,
                               is_new=True, **self._to_persist)
        else:
            # Object exists in CheddarGetter, this is just an update
            xml = self.request('/customers/edit', code=self._code,
                               **self._to_persist)

        # Reload the current customer object
        for customer_xml in xml.getiterator(tag='customer'):
            self._load_from_xml(customer_xml)

        # We've saved successfully, we don't want to persist the changes again
        self._to_persist = {}
        self.subscription._to_persist = {}
        for datum in self.meta_data:
            datum._to_persist = {}

        return self

    def update_metadata(self, name, value):
        for datum in self.meta_data:
            if datum.name == name:
                datum.value = value
                return
        # No existing metadata with that name, create a new one
        self.meta_data.append(MetaDatum(name=name, value=value))


class Plan(CheddarObject):

    __serialize__ = [
        'billing_frequency',
        'trial_days',
        'next_invoice_billing_datetime',
        'billing_frequency_quantity',
        'billing_frequency_unit',
        'recurring_charge_amount',
        'is_free',
        'is_active',
        'name',
        'items',
        'code'
    ]

    @classmethod
    def all(cls):
        plans = []
        try:
            xml = cls.request('/plans/get')
            for plan_xml in xml.getiterator(tag='plan'):
                plans.append(Plan.from_xml(plan_xml))
            return plans
        except NotFound:
            return []

    @classmethod
    def get(cls, code):
        try:
            xml = cls.request('/plans/get', code=code)
            for plan_xml in xml.getiterator(tag='plan'):
                return Plan.from_xml(plan_xml)
        except NotFound:
            return []

    def save(self):
        raise NotImplementedError

    def delete(self):
        self.request('/plans/delete', code=self._code)

    @classmethod
    def get_item():
        pass


class GatewayAccount(CheddarObject):

    __serialize__ = [
        'gateway'
    ]


class Subscription(CheddarObject):

    __serialize__ = [
        'cc_last_four',
        'cc_company',
        'cc_state',
        'cc_type',
        'cc_city',
        'cc_zip',
        'cc_country',
        'cc_first_name',
        'cc_last_name',
        'cc_email',
        'cc_expiration_date',
        'cc_address',
        'created_datetime',
        'canceled_datetime',
        'gateway_account',
        'cancel_type',
        'plan',
        'redirect_url'
    ]

    def __init__(self, **kwargs):
        # Create an empty plan object because newly instantiated subscriptions
        # should have a plan
        self.plans = []
        self.plans.append(Plan())
        super(Subscription, self).__init__(**kwargs)

    def __getattr__(self, key):
        # Proxy plan_code to the plan object
        if inflection.underscore(key) == 'plan_code':
            return self.plan.code
        return super(Subscription, self).__getattr__(key)

    def __setattr__(self, key, value):
        # Intercept plan code and handle it appropriately
        if inflection.underscore(key) == 'plan_code' and \
                value is not self.plan.code:
            previous_plan = self.plans.pop(0)
            # Add the new plan to the subscriptions plans
            self.plans.insert(0, Plan.get(value))

            if previous_plan and value != previous_plan.code:
                # Get the plan_code from the current plan and add it to our
                # data to be saved if this is a plan change
                self._to_persist['plan_code'] = self.plan.code

        if inflection.underscore(key) in ['cc_first_name', 'cc_last_name',
                                          'cc_number', 'cc_expiration',
                                          'cc_card_code', 'method']:
            # Always persist these fields in case this is a subscription
            # change (plan or payment change)
            self._to_persist[inflection.underscore(key)] = value
        else:
            super(Subscription, self).__setattr__(key, value)

    @property
    def plan(self):
        return self.plans[0]

    def save(self):
        """Save the subscription to CheddarGetter. The CheddarGetter API does
        not do allow the creation of a subscription unless a customer is created
        at the same time. Calling this save method will save the parent
        customer if this subscription is new (completely new or a reactivation)
        and in other cases the subscription is being edited."""
        # If this is a new subscription save the parent customer object instead
        # OR if this is a previously cancelled subscription we need to save the
        # customer and associated subscription to create a new subscription.
        if self.is_new() or self.cancel_type == 'customer':
            if self.customer._is_dirty():
                self.customer.save()
            return self

        # This is not a new customer or a reactivate of a cancelled
        # subscription so it must be a subscription modification

        # Do nothing if there is nothing to update
        if not self._to_persist:
            return self

        # Convert keys to camel case
        for key in copy.copy(self._to_persist):
            if '_' in key:
                self._to_persist[inflection.camelize(key, False)] = \
                        self._to_persist[key]
                del self._to_persist[key]

        xml = self.request('/customers/edit-subscription',
                           code=self.customer.code, **self._to_persist)

        # Reload updated data from response
        for subscription_xml in xml.getiterator(tag='subscription'):
            self._load_from_xml(subscription_xml)
            break
        return self

    def delete(self):
        xml = self.request('/customers/cancel', code=self.customer.code)
        for subscription_xml in xml.getiterator(tag='subscription'):
            self._load_from_xml(subscription_xml)
            break


class Invoice(CheddarObject):
    pass


class Item(CheddarObject):

    __serialize__ = [
        'name',
        'quantity_included'
    ]


class MetaDatum(CheddarObject):

    def __init__(self, parent=None, **kwargs):
        super(MetaDatum, self).__init__(parent, **kwargs)

    def __setattr__(self, key, value):
        """Custom setattr method for metadata objects so that we don't interfere
        with the name of the metadata when doing the camelcase/underscore
        conversion."""
        if key[0] == '_':
            self.__dict__[key] = value
        elif key == 'id':
            raise AttributeError('CheddarGetter ID is immutable')
        else:
            if key not in self._data or self._data[key] != value:
                self._to_persist[key] = value
            self._data[key] = value

    def __getattr__(self, key):
        """Custom getattr method for metadata objects so that we don't interfere
        with the name of the metadata when doing the camelcase/underscore
        conversion."""
        if key == 'id':
            return self.__dict__['id']
        elif key[0] == '_' or key in self.__dict__:
            return self.__dict__[key]
        elif key in self._to_persist:
            return self._to_persist[key]
        elif key in self._data:
            return self._data[key]
        else:
            raise AttributeError, 'Key {} does not exist'.format(key)

