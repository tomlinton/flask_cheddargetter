# -*- coding: utf-8 -*-

class CheddarException(Exception):

    def __init__(self, error_id, code, message, aux_code=None):
        self.error_id = error_id
        self.code = code
        self.aux_code = aux_code
        self.message = message


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

