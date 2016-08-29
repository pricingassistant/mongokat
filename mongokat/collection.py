from .utils import dotdict, json_clone
from bson import ObjectId
from bson.codec_options import CodecOptions
from pymongo import ReadPreference, WriteConcern, ReturnDocument, read_preferences
import collections
import base64
from .document import Document
from .exceptions import MultipleResultsFound, ImmutableDocumentError, ProtectedFieldsError


def _param_fields(kwargs, fields):
  """
    Normalize the "fields" argument to most find methods
  """
  if fields is None:
    return
  if type(fields) in [list, set, frozenset, tuple]:
    fields = {x: True for x in fields}
  if type(fields) == dict:
    fields.setdefault("_id", False)
  kwargs["projection"] = fields


def find_method(func):
  """
    Decorator that manages smart defaults or transforms for common find methods:

     - fields/projection: list of fields to be returned. Contrary to pymongo, _id won't be added automatically
     - json: performs a json_clone on the results. Beware of performance!
     - timeout
     - return_document
  """
  def wrapped(*args, **kwargs):

    # Normalize the fields argument if passed as a positional param.
    if len(args) == 3 and func.__name__ in ("find", "find_one", "find_by_id", "find_by_ids"):
      _param_fields(kwargs, args[2])
      args = (args[0], args[1])
    elif "fields" in kwargs:
      _param_fields(kwargs, kwargs["fields"])
      del kwargs["fields"]
    elif "projection" in kwargs:
      _param_fields(kwargs, kwargs["projection"])

    if "timeout" in kwargs:
      kwargs["no_cursor_timeout"] = not bool(kwargs["timeout"])
      del kwargs["timeout"]

    if "spec" in kwargs:
      kwargs["filter"] = kwargs["spec"]
      del kwargs["spec"]

    if kwargs.get("return_document") == "after":
        kwargs["return_document"] = ReturnDocument.AFTER
    elif kwargs.get("return_document") == "before":
        kwargs["return_document"] = ReturnDocument.BEFORE

    ret = func(*args, **kwargs)

    if kwargs.get("json"):
      ret = json_clone(ret)

    return ret

  return wrapped


def patch_cursor(cursor, batch_size=None, limit=None, skip=None, sort=None, **kwargs):
  """
    Adds batch_size, limit, sort parameters to a DB cursor
  """

  if type(batch_size) == int:
    cursor.batch_size(batch_size)

  if limit is not None:
    cursor.limit(limit)

  if sort is not None:
    cursor.sort(sort)

  if skip is not None:
    cursor.skip(skip)


class Collection(object):
    """ mongokat.Collection wraps a pymongo.collection.Collection """

    __collection__ = None
    __database__ = None
    document_class = Document
    structure = None
    immutable = False
    protected_fields = ()

    def __init__(self, collection=None, database=None, client=None):
        """ You can pass a pymongo collection object directly, or rely
            on the __collection__ and/or __database__ attributes
        """

        if collection:
            self.collection = collection
            self.database = collection.database
            self.client = self.database.client
        elif database and self.__collection__:
            self.database = database
            self.client = self.database.client
            self.collection = self.database[self.__collection__]
        elif client and self.__database__ and self.__collection__:
            self.client = client
            self.database = self.client[self.__database__]
            self.collection = self.database[self.__collection__]
        else:
            raise Exception("Not enough parameters given to identify the right collection!")

    def __call__(self, *args, **kwargs):
        """ Instanciates a new *Document* from this collection """
        kwargs["mongokat_collection"] = self
        return self.document_class(*args, **kwargs)

    #
    #
    # READ-ONLY METHODS
    #
    #

    def exists(self, query, **args):
        """
        Returns True if the search matches at least one document
        """
        return bool(self.find(query, **args).limit(1).count())

    def count(self, *args, **kwargs):
        return self._collection_with_options(kwargs).count(*args, **kwargs)

    def distinct(self, *args, **kwargs):
        return self._collection_with_options(kwargs).distinct(*args, **kwargs)

    def group(self, *args, **kwargs):
        return self._collection_with_options(kwargs).group(*args, **kwargs)

    @find_method
    def aggregate(self, *args, **kwargs):

        # Fix weird pymongo inconsistency https://github.com/mongodb/mongo-python-driver/blob/6865ba72edcda31c717037435e7985e9e4139dd9/test/test_crud.py#L85
        if "batch_size" in kwargs:
            kwargs["batchSize"] = kwargs["batch_size"]
            del kwargs["batch_size"]

        return self._collection_with_options(kwargs).aggregate(*args, **kwargs)

    @find_method
    def find(self, *args, **kwargs):
        return self._collection_with_options(kwargs).find(*args, **kwargs)

    def _collection_with_options(self, kwargs):
        """ Returns a copy of the pymongo collection with various options set up """

        # class DocumentClassWithFields(self.document_class):
        #     _fetched_fields = kwargs.get("projection")
        #     mongokat_collection = self

        read_preference = kwargs.get("read_preference") or getattr(self.collection, "read_preference", None) or ReadPreference.PRIMARY

        if "read_preference" in kwargs:
            del kwargs["read_preference"]

        # Simplified tag usage
        if "read_use" in kwargs:
            if kwargs["read_use"] == "primary":
                read_preference = ReadPreference.PRIMARY
            elif kwargs["read_use"] == "secondary":
                read_preference = ReadPreference.SECONDARY
            elif kwargs["read_use"] == "nearest":
                read_preference = ReadPreference.NEAREST
            elif kwargs["read_use"]:
                read_preference = read_preferences.Secondary(tag_sets=[{"use": kwargs["read_use"]}])
            del kwargs["read_use"]

        write_concern = None
        if kwargs.get("w") is 0:
            write_concern = WriteConcern(w=0)
        elif kwargs.get("write_concern"):
            write_concern = kwargs.get("write_concern")

        codec_options = CodecOptions(
            document_class=(
                self.document_class,
                {
                    "fetched_fields": kwargs.get("projection"),
                    "mongokat_collection": self
                }
            )
        )

        return self.collection.with_options(
            codec_options=codec_options,
            read_preference=read_preference,
            write_concern=write_concern
        )

    @find_method
    def find_one(self, *args, **kwargs):
        """
        Get a single document from the database.
        """
        doc = self._collection_with_options(kwargs).find_one(*args, **kwargs)
        if doc is None:
            return None

        return doc

    @find_method
    def find_by_id(self, _id, **kwargs):
        """
        Pass me anything that looks like an _id : str, ObjectId, {"_id": str}, {"_id": ObjectId}
        """

        if type(_id) == dict and _id.get("_id"):
            return self.find_one({"_id": ObjectId(_id["_id"])}, **kwargs)

        return self.find_one({"_id": ObjectId(_id)}, **kwargs)

    @find_method
    def find_by_ids(self, _ids, projection=None, **kwargs):
        """
            Does a big _id:$in query on any iterator
        """

        id_list = [ObjectId(_id) for _id in _ids]

        if len(_ids) == 0:
            return []  # FIXME : this should be an empty cursor !

        # Optimized path when only fetching the _id field.
        # Be mindful this might not filter missing documents that may not have been returned, had we done the query.
        if projection is not None and list(projection.keys()) == ["_id"]:
            return [self({"_id": x}, fetched_fields={"_id": True}) for x in id_list]
        else:
            return self.find({"_id": {"$in": id_list}}, projection=projection, **kwargs)

    @find_method
    def find_by_b64id(self, _id, **kwargs):
        """
        Pass me a base64-encoded ObjectId
        """

        return self.find_one({"_id": ObjectId(base64.b64decode(_id))}, **kwargs)

    @find_method
    def find_by_b64ids(self, _ids, **kwargs):
        """
        Pass me a list of base64-encoded ObjectId
        """

        return self.find_by_ids([ObjectId(base64.b64decode(_id)) for _id in _ids], **kwargs)

    def list_column(self, *args, **kwargs):
        """
            Return one field as a list
        """
        return list(self.iter_column(*args, **kwargs))

    def iter_column(self, query=None, field="_id", **kwargs):
        """
            Return one field as an iterator.
            Beware that if your query returns records where the field is not set, it will raise a KeyError.
        """
        find_kwargs = {
            "projection": {"_id": False}
        }
        find_kwargs["projection"][field] = True

        cursor = self._collection_with_options(kwargs).find(query, **find_kwargs)  # We only want 1 field: bypass the ORM

        patch_cursor(cursor, **kwargs)

        return (dotdict(x)[field] for x in cursor)

    def find_random(self, **kwargs):
        """
        return one random document from the collection
        """
        import random
        max = self.count(**kwargs)
        if max:
            num = random.randint(0, max - 1)
            return next(self.find(**kwargs).skip(num))

    def one(self, *args, **kwargs):
        bson_obj = self.find(*args, **kwargs)
        count = bson_obj.count()
        if count > 1:
            raise MultipleResultsFound("%s results found" % count)
        elif count == 1:
            return next(bson_obj)

    #
    #
    # WRITE METHODS
    #
    #

    def insert(self, data, return_object=False):
        """ Inserts the data as a new document. """

        obj = self(data)  # pylint: disable=E1102
        obj.save()

        if return_object:
            return obj
        else:
            return obj["_id"]

    # http://api.mongodb.org/python/current/api/pymongo/collection.html

    def bulk_write(self, *args, **kwargs):
        """ Hook are not supported for this method! """
        return self.collection.bulk_write(*args, **kwargs)

    def insert_one(self, document, **kwargs):
        ret = self.collection.insert_one(document, **kwargs)
        self.trigger("after_save", ids=[ret.inserted_id], replacements=[document])
        return ret

    def insert_many(self, documents, **kwargs):
        ret = self.collection.insert_many(documents, **kwargs)
        self.trigger("after_save", ids=ret.inserted_ids, replacements=documents)
        return ret

    def replace_one(self, filter, replacement, **kwargs):

        if self.immutable:
            raise ImmutableDocumentError()

        if not kwargs.get("allow_protected_fields"):
            self._check_protected_fields(replacement)
        else:
            del kwargs["allow_protected_fields"]

        before_doc = None
        if self.has_trigger("before_save") or self.has_trigger("after_save"):
            before_doc = self.find_one(filter, read_use="primary", projection=["_id"])
            if before_doc:
                self.trigger("before_save", replacements=[replacement], ids=[before_doc["_id"]])

        ret = self.collection.replace_one(filter, replacement, **kwargs)

        if ret.modified_count is 0:
            return ret
        elif ret.upserted_id:
            self.trigger("after_save", replacements=[replacement], ids=[ret.upserted_id])
        elif before_doc:
            self.trigger("after_save", replacements=[replacement], ids=[before_doc["_id"]])

        return ret

    def update_one(self, filter, update, **kwargs):

        if self.immutable:
            raise ImmutableDocumentError()

        if "$set" in update:
            if not kwargs.get("allow_protected_fields"):
                self._check_protected_fields(update["$set"])
            else:
                del kwargs["allow_protected_fields"]

        before_doc = None
        if self.has_trigger("before_save") or self.has_trigger("after_save"):
            before_doc = self.find_one(filter, read_use="primary", projection=["_id"])
            if before_doc:
                self.trigger("before_save", update=update, ids=[before_doc["_id"]])

        ret = self.collection.update_one(filter, update, **kwargs)

        if ret.modified_count is 0:
            return ret
        elif ret.upserted_id:
            self.trigger("after_save", update=update, ids=[ret.upserted_id])
        elif before_doc:
            self.trigger("after_save", update=update, ids=[before_doc["_id"]])

        return ret

    def update_many(self, filter, update, **kwargs):

        if self.immutable:
            raise ImmutableDocumentError()

        if "$set" in update:
            if not kwargs.get("allow_protected_fields"):
                self._check_protected_fields(update["$set"])
            else:
                del kwargs["allow_protected_fields"]

        before_ids = None
        if self.has_trigger("before_save") or self.has_trigger("after_save"):
            before_ids = self.list_column(filter, read_use="primary")
            if before_ids:
                self.trigger("before_save", update=update, ids=before_ids)

        ret = self.collection.update_many(filter, update, **kwargs)

        if ret.modified_count is 0:
            return ret
        elif before_ids:
            self.trigger("after_save", ids=before_ids, update=update)

        return ret

    def delete_one(self, filter, **kwargs):
        doc = None
        if self.has_trigger("before_delete") or self.has_trigger("after_delete"):
            doc = self.find_one(filter, read_use="primary")
            self.trigger("before_delete", documents=[doc])

        ret = self.collection.delete_one(filter, **kwargs)

        if doc is not None:
            self.trigger("after_delete", documents=[doc])

        return ret

    def delete_many(self, filter, **kwargs):
        docs = []
        if self.has_trigger("before_delete") or self.has_trigger("after_delete"):
            docs = list(self.find(filter, read_use="primary"))
            self.trigger("before_delete", documents=docs)

        ret = self.collection.delete_many(filter, **kwargs)

        if len(docs) > 0:
            self.trigger("after_delete", documents=docs)

        return ret

    @find_method
    def find_one_and_delete(self, filter, **kwargs):
        self.trigger("before_delete", filter=filter)
        ret = self.collection.find_one_and_delete(filter, **kwargs)
        if ret is None:
            return None
        doc = self(ret, fetched_fields=kwargs.get("projection"))
        self.trigger("after_delete", documents=[doc])
        return doc

    @find_method
    def find_one_and_replace(self, filter, replacement, **kwargs):

        if self.immutable:
            raise ImmutableDocumentError()

        if not kwargs.get("allow_protected_fields"):
            self._check_protected_fields(replacement)
        else:
            del kwargs["allow_protected_fields"]

        ret = self.collection.find_one_and_replace(filter, replacement, **kwargs)
        if ret is None:
            return None
        doc = self(ret, fetched_fields=kwargs.get("projection"))
        self.trigger("after_save", documents=[doc], replacements=[replacement])
        return doc

    @find_method
    def find_one_and_update(self, filter, update, **kwargs):

        if self.immutable:
            raise ImmutableDocumentError()

        if "$set" in update:
            if not kwargs.get("allow_protected_fields"):
                self._check_protected_fields(update["$set"])
            else:
                del kwargs["allow_protected_fields"]

        if self.has_trigger("before_save"):
            before_id = self.find_one(filter, read_use="primary", projection=["_id"])
            if before_id:
                self.trigger("before_save", update=update, ids=[before_id["_id"]])

        ret = self.collection.find_one_and_update(filter, update, **kwargs)
        if ret is None:
            return None
        doc = self(ret, fetched_fields=kwargs.get("projection"))
        self.trigger("after_save", documents=[doc], update=update)
        return doc

    #
    #
    # EVENTS MANAGEMENT
    #
    #

    def has_trigger(self, event):
        """ Does this trigger need to run? """
        return hasattr(self.document_class, event)

    def trigger(self, event, filter=None, update=None, documents=None, ids=None, replacements=None):
        """ Trigger the after_save hook on documents, if present. """

        if not self.has_trigger(event):
            return

        if documents is not None:
            pass
        elif ids is not None:
            documents = self.find_by_ids(ids, read_use="primary")
        elif filter is not None:
            documents = self.find(filter, read_use="primary")
        else:
            raise Exception("Trigger couldn't filter documents")

        for doc in documents:
            getattr(doc, event)(update=update, replacements=replacements)
    #
    #
    # FOR BACKWARDS-COMPATIBILITY
    #
    #

    @property
    def connection(self):
        return self.client

    @property
    def db(self):
        return self.database

    def save(self, to_save, **kwargs):

        if self.immutable and "_id" in to_save:
            raise ImmutableDocumentError()

        if not kwargs.get("allow_protected_fields"):
            self._check_protected_fields(to_save)
        else:
            del kwargs["allow_protected_fields"]

        if "safe" in kwargs:
            kwargs["w"] = 0 if not kwargs["safe"] else 1
            del kwargs["safe"]

        if self.has_trigger("before_save") and "_id" in to_save:
            self.trigger("before_save", replacements=[to_save], ids=[to_save["_id"]])

        _id = self.collection.save(to_save, **kwargs)

        self.trigger("after_save", replacements=[to_save], ids=[_id])
        return _id

    def update(self, spec, document, **kwargs):

        if self.immutable:
            raise ImmutableDocumentError()

        if "$set" in document:
            if not kwargs.get("allow_protected_fields"):
                self._check_protected_fields(document["$set"])
            else:
                del kwargs["allow_protected_fields"]

        before_ids = None
        if self.has_trigger("before_save") or self.has_trigger("after_save"):
            before_ids = self.list_column(spec, read_use="primary")
            if before_ids:
                self.trigger("before_save", ids=before_ids, update=document)

        ret = self.collection.update(spec, document, **kwargs)
        self.trigger("after_save", ids=before_ids, update=document)
        return ret

    def remove(self, spec_or_id=None, **kwargs):
        docs = []

        if self.has_trigger("before_delete") or self.has_trigger("after_delete"):
            limit = 0
            if spec_or_id is None:
                filter = {}
            elif not isinstance(spec_or_id, collections.Mapping):
                filter = {"_id": spec_or_id}
            else:
                filter = spec_or_id
                limit = 1 if kwargs.get("multi") is False else 0

            docs = list(self.find(filter, read_use="primary", limit=limit))
            self.trigger("before_delete", documents=docs)

        ret = self.collection.remove(spec_or_id=spec_or_id, **kwargs)

        if len(docs) > 0:
            self.trigger("after_delete", documents=docs)

        return ret

    def find_and_modify(self, query={}, update=None, **kwargs):

        if self.immutable:
            raise ImmutableDocumentError()

        if "$set" in update:
            if not kwargs.get("allow_protected_fields"):
                self._check_protected_fields(update["$set"])
            else:
                del kwargs["allow_protected_fields"]

        ret = self.collection.find_and_modify(query=query, update=update, **kwargs)
        if ret is None:
            return None
        self.trigger("after_save", ids=[ret["_id"]], update=update)
        return self(ret, fetched_fields=kwargs.get("projection"))

    def get_from_id(self, _id):
        return self.find_one({"_id": _id})

    def fetch(self, spec=None, *args, **kwargs):
        """
        return all document which match the structure of the object
        `fetch()` takes the same arguments than the the pymongo.collection.find method.
        The query is launch against the db and collection of the object.
        """
        if spec is None:
            spec = {}
        for key in self.structure:
            if key in spec:
                if isinstance(spec[key], dict):
                    spec[key].update({'$exists': True})
            else:
                spec[key] = {'$exists': True}
        return self.find(spec, *args, **kwargs)

    def fetch_one(self, *args, **kwargs):
        """
        return one document which match the structure of the object
        `fetch_one()` takes the same arguments than the the pymongo.collection.find method.
        If multiple documents are found, raise a MultipleResultsFound exception.
        If no document is found, return None
        The query is launch against the db and collection of the object.
        """
        bson_obj = self.fetch(*args, **kwargs)
        count = bson_obj.count()
        if count > 1:
            raise MultipleResultsFound("%s results found" % count)
        elif count == 1:
            # return self(bson_obj.next(), fetched_fields=kwargs.get("projection"))
            return next(bson_obj)

    def _check_protected_fields(self, data):

        if len(self.protected_fields):
            forbidden_fields = set(data.keys()) & set(self.protected_fields)
            if len(forbidden_fields) > 0:
                raise ProtectedFieldsError("cannot set those keys without allow_protected_fields : %s" % forbidden_fields)
