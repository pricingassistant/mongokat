"""
Welcome to the API documentation for MongoKat.

Please see the [README on GitHub](https://github.com/pricingassistant/mongokat) for more info about MongoKat.
"""

from . import _bson
import pymongo

# This is the only monkey-patch needed to use our own bson.decode_all function,
# which implements https://jira.mongodb.org/browse/PYTHON-175
pymongo.helpers.bson = _bson

from .collection import Collection, find_method
from .document import Document
