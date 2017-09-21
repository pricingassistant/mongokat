import base64
import copy
from .utils import dotdict
from uuid import UUID, uuid4
from bson import BSON
from pymongo.errors import OperationFailure
import collections

try:
    import cPickle
except:
    import _pickle as cPickle


def _flatten_fetched_fields(fields_arg):
    """ this method takes either a kwargs 'fields', which can be a dict :
    {"_id": False, "store": 1, "url": 1} or a list : ["store", "flag", "url"]
    and returns a tuple : ("store", "flag").
    it HAS to be a tuple, so that it is not updated by the different instances
    """
    if fields_arg is None:
        return None
    if isinstance(fields_arg, dict):
        return tuple(sorted([k for k in list(fields_arg.keys()) if fields_arg[k]]))
    else:
        return tuple(sorted(fields_arg))


class Document(dict):

    _initialized_with_doc = False
    _fetched_fields = None
    mongokat_collection = None
    gen_skel = True

    def __init__(self, doc=None, mongokat_collection=None, fetched_fields=None, gen_skel=None):

        if mongokat_collection is not None:
            self.mongokat_collection = mongokat_collection
        self.collection = self.mongokat_collection.collection

        if fetched_fields is not None:
            self._fetched_fields = fetched_fields
        self._fetched_fields = _flatten_fetched_fields(self._fetched_fields)

        if gen_skel is not None:
            self.gen_skel = gen_skel

        if doc is not None:
            for k, v in doc.items():
                self[k] = v

        if not self._fetched_fields:
            self._initialized_with_doc = True

        if self.gen_skel:
            self.generate_skeleton()

    def __str__(self):
        return "%s(%s)" % (self.__class__.__name__, dict(self))

    def __hash__(self):
        if '_id' in self:
            value = self['_id']
            return value.__hash__()
        else:
            raise TypeError("A Document is not hashable if it is not saved. Save the document before hashing it")

    def __deepcopy__(self, memo={}):
        obj = self.__class__(doc=cPickle.loads(cPickle.dumps(self.copy())), gen_skel=self.gen_skel, mongokat_collection=self.mongokat_collection, fetched_fields=self._fetched_fields)
        obj.__dict__ = self.__dict__.copy()
        return obj

    # def __reduce__(self):
    #     return (self.__class__, (self.copy(), self.mongokat_collection, self._fetched_fields, self.gen_skel))

    @property
    def b64id(self):
        """ Returns the document's _id as a base64-encoded string """
        return base64.b64encode(self["_id"].binary)

    def ensure_fields(self, fields, force_refetch=False):
        """ Makes sure we fetched the fields, and populate them if not. """

        # We fetched with fields=None, we should have fetched them all
        if self._fetched_fields is None or self._initialized_with_doc:
            return

        if force_refetch:
            missing_fields = fields
        else:
            missing_fields = [f for f in fields if f not in self._fetched_fields]

        if len(missing_fields) == 0:
            return

        if "_id" not in self:
            raise Exception("Can't ensure_fields because _id is missing")

        self.refetch_fields(missing_fields)

    def refetch_fields(self, missing_fields):
        """ Refetches a list of fields from the DB """
        db_fields = self.mongokat_collection.find_one({"_id": self["_id"]}, fields={k: 1 for k in missing_fields})

        self._fetched_fields += tuple(missing_fields)

        if not db_fields:
            return

        for k, v in db_fields.items():
            self[k] = v

    def unset_fields(self, fields):
        """ Removes this list of fields from both the local object and the DB. """

        self.mongokat_collection.update_one({"_id": self["_id"]}, {"$unset": {
            f: 1 for f in fields
        }})

        for f in fields:
            if f in self:
                del self[f]

    def reload(self):
        """
        allow to refresh the document, so after using update(), it could reload
        its value from the database.

        Be carreful : reload() will erase all unsaved values.

        If no _id is set in the document, a KeyError is raised.

        """

        old_doc = self.mongokat_collection.find_one({"_id": self['_id']}, read_use="primary")

        if not old_doc:
            raise OperationFailure('Can not reload an unsaved document.'
                                   ' %s is not found in the database. Maybe _id was a string and not ObjectId?' % self['_id'])
        else:
            for k in list(self.keys()):
                del self[k]
            self.update(dotdict(old_doc))

        self._initialized_with_doc = False

    def delete(self):
        """
        delete the document from the collection from his _id.
        """
        self.mongokat_collection.remove({'_id': self['_id']})

    def save(self, force=False, uuid=False, **kwargs):
        """
          REPLACES the object in DB. This is forbidden with objects from find() methods unless force=True is given.
        """

        if not self._initialized_with_doc and not force:
            raise Exception("Cannot save a document not initialized from a Python dict. This might remove fields from the DB!")

        self._initialized_with_doc = False

        if '_id' not in self:
            if uuid:
                self['_id'] = str("%s-%s" % (self.mongokat_collection.__class__.__name__, uuid4()))

        return self.mongokat_collection.save(self, **kwargs)

    def save_partial(self, data=None, allow_protected_fields=False, **kwargs):
        """ Saves just the currently set fields in the database. """

        # Backwards compat, deprecated argument
        if "dotnotation" in kwargs:
            del kwargs["dotnotation"]

        if data is None:

            data = dotdict(self)
            if "_id" not in data:
                raise KeyError("_id must be set in order to do a save_partial()")
            del data["_id"]

        if len(data) == 0:
          return

        if not allow_protected_fields:
            self.mongokat_collection._check_protected_fields(data)

        apply_on = dotdict(self)

        self._initialized_with_doc = False

        self.mongokat_collection.update_one({"_id": self["_id"]}, {"$set": data}, **kwargs)

        for k, v in data.items():
            apply_on[k] = v

        self.update(dict(apply_on))

    def __generate_skeleton(self, doc, struct, path=""):

        for key in struct:
            if type(key) is type:
                new_key = "$%s" % key.__name__
            else:
                new_key = key
            new_path = ".".join([path, new_key]).strip('.')
            #
            # Automatique generate the skeleton with NoneType
            #
            if type(key) is not type and key not in doc:
                if isinstance(struct[key], dict):
                    if isinstance(struct[key], collections.Callable):
                        doc[key] = struct[key]()
                    else:
                        doc[key] = type(struct[key])()
                elif struct[key] is dict:
                    doc[key] = {}
                elif isinstance(struct[key], list):
                    doc[key] = type(struct[key])()
                # elif isinstance(struct[key], CustomType):
                #     if struct[key].init_type is not None:
                #         doc[key] = struct[key].init_type()
                #     else:
                #         doc[key] = None
                elif struct[key] is list:
                    doc[key] = []
                elif isinstance(struct[key], tuple):
                    doc[key] = [None for _ in range(len(struct[key]))]
                else:
                    doc[key] = None
            #
            # if the value is a dict, we have a another structure to validate
            #
            if isinstance(struct[key], dict) and type(key) is not type:
                self.__generate_skeleton(doc[key], struct[key], new_path)

    def generate_skeleton(self):
        if self.mongokat_collection.structure is not None:
            self.__generate_skeleton(self, self.mongokat_collection.structure)

    def get_size(self):
        """
        return the size of the underlying bson object
        """
        try:
            return len(BSON.encode(self))
        except:
            return None

    def validate(self):
        """ We do not support validation yet. """
        pass
