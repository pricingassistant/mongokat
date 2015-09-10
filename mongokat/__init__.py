"""
Welcome to the API documentation for MongoKat.

Please see the [README on GitHub](https://github.com/pricingassistant/mongokat) for more info about MongoKat.
"""

from . import _bson

import pymongo

# This is the only monkey-patch needed to use our own bson.decode_all function,
# which implements https://jira.mongodb.org/browse/PYTHON-175
pymongo.helpers.bson = _bson

import bson


# This other monkey-patch is needed to disable the type check on document_class, because
# we also can pass a tuple to use additional kwargs in the document_class instanciation.
class CodecOptionsWithoutCheck(bson.codec_options.CodecOptions):
  def __new__(cls, document_class=dict,
              tz_aware=False, uuid_representation=bson.codec_options.PYTHON_LEGACY):
      # if not issubclass(document_class, MutableMapping):
      #     raise TypeError("document_class must be dict, bson.son.SON, or "
      #                     "another subclass of collections.MutableMapping")
      if not isinstance(tz_aware, bool):
          raise TypeError("tz_aware must be True or False")
      if uuid_representation not in bson.codec_options.ALL_UUID_REPRESENTATIONS:
          raise ValueError("uuid_representation must be a value "
                           "from bson.binary.ALL_UUID_REPRESENTATIONS")

      return tuple.__new__(
          cls, (document_class, tz_aware, uuid_representation))


bson.codec_options.CodecOptions = CodecOptionsWithoutCheck

from .collection import Collection, find_method
from .document import Document
