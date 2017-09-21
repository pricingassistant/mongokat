import copy

from bson import ObjectId


def test_deepcopy(Sample):

    s1 = Sample({"name": "X1", "flt": 2.0, "id": ObjectId()})

    s2 = copy.deepcopy(s1)

    assert s2["id"] == s1["id"]
    assert s2["name"] == s1["name"]
    assert s2["flt"] == s1["flt"]
    assert id(s2) != id(s1)
    assert id(s2["id"]) != id(s1["id"])


# def test_pickle(Sample):
#     import pickle
#     s1 = Sample({"name": "X1", "url": "http://example.com", "id": ObjectId()})

#     s2 = pickle.loads(pickle.dumps(s1))

#     print s2
#     assert s2["id"] == s1["id"]
#     assert s2["name"] == s1["name"]
#     assert id(s2) != id(s1)


# def test_cpickle(Sample):
#     import cPickle
#     s1 = Sample({"name": "X1", "url": "http://example.com", "id": ObjectId()})

#     s2 = cPickle.loads(cPickle.dumps(s1))

#     print s2
#     assert s2["id"] == s1["id"]
#     assert s2["name"] == s1["name"]
#     assert id(s2) != id(s1)
