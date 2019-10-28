
import bson
import sys
from bson.codec_options import DEFAULT_CODEC_OPTIONS, CodecOptions, _raw_document_class


def decode_all(data, codec_options=DEFAULT_CODEC_OPTIONS):
    if not isinstance(codec_options, CodecOptions):
        raise bson._CODEC_OPTIONS_TYPE_ERROR
    docs = []
    position = 0
    end = len(data) - 1
    use_raw = _raw_document_class(codec_options.document_class)
    try:
        while position < end:
            obj_size = bson._UNPACK_INT(data[position:position + 4])[0]
            if len(data) - position < obj_size:
                raise bson.InvalidBSON("invalid object size")
            obj_end = position + obj_size - 1
            if data[obj_end:position + obj_size] != b"\x00":
                raise bson.InvalidBSON("bad eoo")
            if use_raw:
                docs.append(
                    codec_options.document_class(
                        data[position:obj_end + 1], codec_options))
            else:
                docs.append(_elements_to_dict(data,
                                              position + 4,
                                              obj_end,
                                              codec_options))
            position += obj_size
        return docs
    except bson.InvalidBSON:
        raise
    except Exception:
        # Change exception type to InvalidBSON but preserve traceback.
        _, exc_value, exc_tb = sys.exc_info()
        bson.reraise(bson.InvalidBSON, exc_value, exc_tb)


def _element_to_dict(data, position, obj_end, opts):
    """Decode a single key, value pair."""
    element_type = data[position:position + 1]
    position += 1
    element_name, position = bson._get_c_string(data, position, opts)
    value, position = bson._ELEMENT_GETTER[element_type](data, position,
                                                        obj_end, opts,
                                                        element_name)
    return element_name, value, position


def _iterate_elements(data, position, obj_end, opts):
    end = obj_end - 1
    while position < end:
        (key, value, position) = _element_to_dict(data, position, obj_end, opts)
        yield key, value, position

def _elements_to_dict(data, position, obj_end, opts, subdocument=None):
    """Decode a BSON document."""
    if type(opts.document_class) == tuple:
        result = opts.document_class[0](**opts.document_class[1]) if not subdocument else dict()
    else:
        result = opts.document_class() if not subdocument else dict()
    pos = position
    for key, value, pos in _iterate_elements(data, position, obj_end, opts):
        if key in ["firstBatch", "nextBatch"] and type(opts.document_class) == tuple:
            batches = []
            for batch in value:
                batch_document = opts.document_class[0](**opts.document_class[1])
                batch_document.update(batch)
                batches.append(batch_document)
            result[key] = batches
        else:
            result[key] = value
    if pos != obj_end:
        raise bson.InvalidBSON('bad object or element length')
    return result


def _get_object(data, position, obj_end, opts, dummy):
    """Decode a BSON subdocument to opts.document_class or bson.dbref.DBRef."""
    obj_size = bson._UNPACK_INT(data[position:position + 4])[0]
    end = position + obj_size - 1
    if data[end:position + obj_size] != b"\x00":
        raise bson.InvalidBSON("bad eoo")
    if end >= obj_end:
        raise bson.InvalidBSON("invalid object length")
    if _raw_document_class(opts.document_class):
        return (opts.document_class(data[position:end + 1], opts),
                position + obj_size)

    obj = _elements_to_dict(data, position + 4, end, opts, subdocument=True)
    position += obj_size
    if "$ref" in obj:
        return (bson.DBRef(obj.pop("$ref"), obj.pop("$id", None),
                      obj.pop("$db", None), obj), position)
    return obj, position
