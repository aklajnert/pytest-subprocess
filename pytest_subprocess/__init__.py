"""Main module"""
from . import exceptions
from .fake_process import FakeProcess

ProcessNotRegisteredError = exceptions.ProcessNotRegisteredError

__all__ = ["FakeProcess", "exceptions", "ProcessNotRegisteredError"]
