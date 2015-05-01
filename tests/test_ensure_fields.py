
def test_document_ensure_fields(Sample):

    assert Sample.count() == 0

    # Instanciate
    new_object = Sample({"name": "XXX", "url": "http://example.com"})

    new_object.ensure_fields(["test"])

    assert "test" not in new_object

    new_object.save()

    obj = Sample.find_one(fields=["url"])

    # FIXME
    # Can't ensure fields when no _id
    # with pytest.raises(Exception):
    #   obj.ensure_fields(["name"])

    obj = Sample.find_one(fields=["url", "_id"])

    assert "name" not in obj

    obj.ensure_fields(["name"])

    assert Sample.count() == 1

    assert obj["name"] == "XXX"

    obj = Sample.find_one(fields=["_id", "name"])

    assert "url" not in obj

    # Update it from elsewhere
    Sample.collection.update({}, {"$set": {"name": "YYY"}})

    obj.ensure_fields(["url", "name"])

    # Only url should have been refreshed
    assert obj["url"] == "http://example.com"
    assert obj["name"] == "XXX"

    obj = Sample.find_one(fields=["_id"])

    obj.ensure_fields(["name"])

    assert obj["name"] == "YYY"

    # Test find()

    obj = list(Sample.find({"_id": new_object["_id"]}, fields={"_id": True, "url": True}))[0]
    assert obj.get("name") is None
    obj.ensure_fields(["name"])
    assert obj["name"] == "YYY"

    obj = list(Sample.find({"_id": new_object["_id"]}, {"_id": True, "url": True, "x": True}))[0]
    assert "x" in obj._fetched_fields
    assert obj.get("name") is None
    obj.ensure_fields(["name"])
    assert obj["name"] == "YYY"

    obj = list(Sample.find(fields=["_id"]))[0]

    obj.ensure_fields(["name"])

    assert obj["name"] == "YYY"

    obj2 = Sample.find_by_id(obj["_id"])
    obj2.unset_fields({"name": 1})

    assert obj2.get("name") is None
    obj.ensure_fields(["name"])
    assert obj2.get("name") is None

    # name should *not* be reloaded yet.
    obj.ensure_fields(["name"])
    assert obj.get("name") is not None

    obj.reload()
    assert obj.get("name") is None

