import copy
import json
from bson import ObjectId
import datetime

try:
  from requests.structures import CaseInsensitiveDict
except:
  CaseInsensitiveDict = None


class _CustomJsonEncoder(json.JSONEncoder):
  def default(self, obj):  # pylint: disable-msg=E0202
    if isinstance(obj, datetime.datetime):
      return obj.isoformat()
    elif isinstance(obj, ObjectId):
      return str(obj)
    elif CaseInsensitiveDict and isinstance(obj, CaseInsensitiveDict):
      return dict(obj)
    elif type(obj) == set:
      return list(obj)
    return json.JSONEncoder.default(self, obj)

_CUSTOM_JSON_ENCODER = _CustomJsonEncoder()


def json_clone(obj):
  return json.loads(_CUSTOM_JSON_ENCODER.encode(obj))


class dotdict(dict):
  """"
  >>> life = dotdict({'bigBang': {'stars': {'planets': {}}}})
  >>> life.bigBang.stars.planets
  {}
  >>> life.bigBang.stars.planets.earth = { 'singleCellLife' : {} }
  >>> life.bigBang.stars.planets
  {'earth': {'singleCellLife': {}}}
  >>> life['bigBang.stars.planets.mars.landers.vikings'] = 2
  >>> life.bigBang.stars.planets.mars.landers.vikings
  2
  >>> 'landers.vikings' in life.bigBang.stars.planets.mars
  True
  >>> life.get('bigBang.stars.planets.mars.landers.spirit', True)
  True
  >>> life.setdefault('bigBang.stars.planets.mars.landers.opportunity', True)
  True
  >>> 'landers.opportunity' in life.bigBang.stars.planets.mars
  True
  >>> life.bigBang.stars.planets.mars
  {'landers': {'opportunity': True, 'vikings': 2}}
  """

  def __init__(self, value=None):
    if value is None:
      pass
    elif isinstance(value, dict):
      for key in value:
        self.__setitem__(key, value[key])
    else:
      raise TypeError('expected dict')

  def __setitem__(self, key, value):
    if '.' in key:
      myKey, restOfKey = key.split('.', 1)
      target = self.setdefault(myKey, dotdict())
      if not isinstance(target, dotdict):
        raise KeyError('cannot set "%s" in "%s" (%s)' % (restOfKey, myKey, repr(target)))
      target[restOfKey] = value
    else:
      if isinstance(value, dict) and not isinstance(value, dotdict):
        value = dotdict(value)
      dict.__setitem__(self, key, value)

  def __getitem__(self, key):
    if '.' not in key:
      return dict.__getitem__(self, key)
    myKey, restOfKey = key.split('.', 1)
    target = dict.__getitem__(self, myKey)
    if not isinstance(target, dotdict):
      raise KeyError('cannot get "%s" in "%s" (%s)' % (restOfKey, myKey, repr(target)))
    return target[restOfKey]

  def __contains__(self, key):
    if '.' not in key:
      return dict.__contains__(self, key)
    myKey, restOfKey = key.split('.', 1)
    if myKey in self:
      target = dict.__getitem__(self, myKey)
    else:
      return False
    if not isinstance(target, dotdict):
      return False
    return restOfKey in target

  def setdefault(self, key, default):
    if key not in self:
      self[key] = default
    return self[key]

  def __deepcopy__(self, memo):
    return copy.deepcopy(dict(self))
