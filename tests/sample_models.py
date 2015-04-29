from mongokat import Collection, Document


class SampleDocument(Document):
    def my_method(self):
        return 1


class SampleCollection(Collection):
    document_class = SampleDocument
