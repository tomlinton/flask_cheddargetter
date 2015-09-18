# -*- coding: utf-8 -*-

class CheddarException(Exception):

    def __init__(self, message, aux_code):
        self.message = message
        self.aux_code = aux_code


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

