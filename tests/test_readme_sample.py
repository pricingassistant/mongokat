
def test_readme_sample():

    # SETUP

    from pymongo import MongoClient
    MongoClient().my_db.my_col.drop()

    # SAMPLE CODE BELOW

    # First, declare a Document/Collection pair (a "model"):

    from mongokat import Collection, Document

    class SampleDocument(Document):

        def my_sum(self):
            return self["a"] + self["b"]

    class SampleCollection(Collection):
        document_class = SampleDocument

        def find_by_a(self, a_value):
            return self.find_one({"a": a_value})

    # Then use it in your code like this:

    from pymongo import MongoClient
    client = MongoClient()
    Sample = SampleCollection(collection=client.my_db.my_col)

    Sample.insert({"a": 1, "b": 2})
    Sample.insert({"a": 2, "b": 3})

    assert Sample.count() == 2

    five = Sample.find_by_a(2)
    assert five.my_sum() == 5
