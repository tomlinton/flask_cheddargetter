# -*- coding: utf-8 -*-

class CheddarException(Exception):
    pass


class NotFound(CheddarException):
    pass


class BadRequest(CheddarException):
    pass


class UnexpectedResponse(CheddarException):
    pass


class GatewayFailure(CheddarException):
    pass


class GatewayConnectionError(CheddarException):
    pass


class ValidationError(CheddarException):
    pass

