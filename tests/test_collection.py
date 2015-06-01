
def test_collection_read_preference():
    from pymongo import MongoClient, ReadPreference
    from mongokat import Collection

    class SampleCollection(Collection):
        __collection__ = "my_col"

    db = MongoClient(read_preference=ReadPreference.SECONDARY)["my_db"]
    sample_collection = SampleCollection(database=db)
    assert sample_collection.collection.read_preference == ReadPreference.SECONDARY
    assert Collection._collection_with_options(sample_collection, {}).read_preference == ReadPreference.SECONDARY
