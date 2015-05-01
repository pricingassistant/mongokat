import pytest
import sample_models
import datetime


def test_collection_find(Sample):

    Sample.insert_one({"name": "XXX", "url": "http://example.com"})

    _id = Sample.find_one()["_id"]

    # Don't include _id by default
    assert dict(Sample.find_one({"name": "XXX"})) == {"name": "XXX", "url": "http://example.com", "_id": _id}
    assert dict(Sample.find_one({"name": "XXX"}, fields=["name"])) == {"name": "XXX"}
    assert dict(Sample.find_one({"name": "XXX"}, fields={"_id": 1, "name": 1})) == {"name": "XXX", "_id": _id}
    assert dict(Sample.find_one({"name": "XXX"}, fields={"name": 1})) == {"name": "XXX"}
    assert dict(Sample.find_one({"name": "XXX"}, fields={"name": True})) == {"name": "XXX"}
    assert dict(Sample.find_one({"name": "XXX"}, fields=set(["name"]))) == {"name": "XXX"}
    assert dict(Sample.find_one({"name": "XXX"}, fields=frozenset(["name"]))) == {"name": "XXX"}
    assert dict(Sample.find_one({"name": "XXX"}, fields=("name", ))) == {"name": "XXX"}


def test_document_no_shared_fields(Sample):

    new_object = Sample({"name": "XXX", "url": "http://example.com"})
    new_object.save()

    cursor1 = Sample.find({"_id": new_object["_id"]}, fields={"_id": True, "url": True})
    cursor2 = Sample.find({"_id": new_object["_id"]}, fields={"_id": True, "name": True})

    obj1 = list(cursor1)
    obj2 = list(cursor2)

    assert "url" in obj1[0]
    assert "name" not in obj1[0]

    assert "url" not in obj2[0]
    assert "name" in obj2[0]


def test_document_reload_if_unset_field(Sample):

    store = Sample({"name": "ab", "url": "mongokit.com"})
    store.save()
    _id = store["_id"]

    # The same
    store2 = Sample.find_one()
    store2["url"] = "x"

    store.unset_fields(["name"])
    store.reload()
    assert store.get("name") is None
    assert store["_id"] == _id
    assert store["url"] == "mongokit.com"

    # This may happen in a different context
    store2.reload()
    assert store2.get("name") is None
    assert store2["_id"] == _id
    assert store2["url"] == "mongokit.com"


def test_document_delete(Sample):

    Sample.insert({"a": 1})

    s = Sample.find_one()
    assert s
    s.delete()

    s = Sample.find_one()
    assert s is None


def test_document_common_methods(Sample):

  from bson import ObjectId
  import collections

  assert Sample.collection.find().count() == 0

  # Instanciate
  new_object = Sample({"name": "XXX", "url": "http://example.com"})

  # Should not save to DB yet.
  assert Sample.collection.find().count() == 0

  # Now save()
  new_object.save()

  # Once the object is in DB, we can't do it anymore.
  with pytest.raises(Exception):
    new_object.save()

  assert type(new_object["_id"]) == ObjectId

  assert Sample.collection.find().count() == 1
  db_object = Sample.collection.find_one()
  assert type(db_object) == dict
  assert db_object["name"] == "XXX"

  # test insert()
  inserted_object = Sample.insert({"name": "ZZZ", "url": "http://example2.com", "stats": {"nb_of_products": 2}})
  assert type(inserted_object) == ObjectId

  assert Sample.collection.find().count() == 2

  # Find back with different methods
  orm_object = Sample.find_by_id(db_object["_id"])
  assert orm_object["name"] == "XXX"
  orm_object = Sample.find_by_id(str(db_object["_id"]))
  assert orm_object["name"] == "XXX"
  orm_object = Sample.find_by_id({"_id": db_object["_id"]})
  assert orm_object["name"] == "XXX"
  orm_object = Sample.find_by_id({"_id": str(db_object["_id"])})
  assert orm_object["name"] == "XXX"
  assert isinstance(orm_object, sample_models.SampleDocument)

  # exists()
  assert Sample.exists({"name": "XXX"})

  # Other find styles
  cursor = Sample.find({"name": "XXX"})
  assert "cursor" in str(type(cursor)).lower()
  orm_objects = list(cursor)
  assert len(orm_objects) == 1
  assert isinstance(orm_objects[0], sample_models.SampleDocument)
  assert orm_objects[0]["name"] == "XXX"

  orm_object = Sample.find_one({"_id": db_object["_id"]})
  assert orm_object["name"] == "XXX"
  assert isinstance(orm_object, sample_models.SampleDocument)

  # TODO - should that not work?
  orm_object = Sample.find_one({"_id": str(db_object["_id"])})
  assert orm_object is None

  col_cursor = Sample.iter_column({"name": "XXX"})
  assert isinstance(col_cursor, collections.Iterable)
  assert list(col_cursor) == [new_object["_id"]]

  col = Sample.list_column({"name": "XXX"}, field="name")
  assert col == ["XXX"]
  col = Sample.list_column({"name": "ZZZ"}, field="stats.nb_of_products")
  assert col == [2]

  with pytest.raises(KeyError):
    Sample.list_column({"name": "ZZZ"}, field="inexistent_field")

  # We should be able to fetch & save partial objects.
  orm_object = Sample.find_by_id(db_object["_id"], fields=["url"])
  assert dict(orm_object).keys() == ["url"]
  assert dict(orm_object)["url"] == "http://example.com"

  # If we save() that, it will create a new object because we lack an _id :(
  with pytest.raises(Exception):
    orm_object.save()

  assert Sample.collection.find().count() == 2

  # FIXME not anymore as we are requesting _id for each query
  # orm_object.save(force=True)

  # assert Sample.collection.find().count() == 3

  orm_object = Sample.find_by_id(db_object["_id"], fields=["url", "_id"])
  assert dict(orm_object) == {"url": "http://example.com", "_id": db_object["_id"]}

  # Change the data a bit and save.
  # This would remove "name" from the doc.
  orm_object["url"] = "http://other.example.com"

  # Not authorized!
  with pytest.raises(Exception):
    orm_object.save()

  assert Sample.collection.find().count() == 2
  db_object = Sample.collection.find_one({"_id": db_object["_id"]})
  assert "name" in db_object

  orm_object.save(force=True)

  # Should not add anything new
  assert Sample.collection.find().count() == 2

  db_object = Sample.collection.find_one({"_id": db_object["_id"]})
  assert "name" not in db_object
  assert db_object["url"] == "http://other.example.com"

  orm_object = Sample.find_by_id(db_object["_id"], fields=["_id"])
  orm_object["name"] = "YYY"

  # This one should not overwrite unset fields.
  orm_object.save_partial()

  db_object = Sample.collection.find_one({"_id": db_object["_id"]})
  assert db_object["name"] == "YYY"
  assert db_object["url"] == "http://other.example.com"

  # Test the reload() method by changing the data from somewhere else
  Sample.collection.update({"_id": db_object["_id"]}, {"$set": {"name": "AAA"}})

  assert orm_object["name"] == "YYY"

  orm_object.reload()

  assert orm_object["name"] == "AAA"

  # Test .update() - local dict update()
  orm_object.update({"name": "BBB"})

  assert orm_object["name"] == "BBB"

  # Should not have changed the DB
  db_object = Sample.collection.find_one({"_id": db_object["_id"]})
  assert db_object["name"] == "AAA"


def test_save_partial_dotdict(Sample):

    now = datetime.datetime.now().replace(microsecond=0)
    store = Sample({
        "name": "XXX",
        "priceparsing": {
            "normal": {
                "consecutiveoks": 10, "lastdatemoderated": now
            }
        }
    })
    store.save()

    store.reload()
    assert store["priceparsing"]["normal"]["consecutiveoks"] == 10

    store.save_partial({"priceparsing.normal.consecutiveoks": 30})
    assert store["priceparsing"]["normal"]["consecutiveoks"] == 30
    assert store["priceparsing"]["normal"]["lastdatemoderated"] == now

    store.reload()
    assert store["priceparsing"]["normal"]["consecutiveoks"] == 30
    assert store["priceparsing"]["normal"]["lastdatemoderated"] == now

