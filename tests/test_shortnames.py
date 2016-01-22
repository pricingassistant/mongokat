from mongokat import Document, Collection


class ShortNamesDocument(Document):
  """ This Document subclass supports limited alias names, as suggested in https://github.com/pricingassistant/mongokat/issues/13

  Note that they don't work in queries, field name lists, or dict(doc). Further subclassing would be necessary
  for that to work. Pull Requests welcome, though we won't include that in MongoKat itself.
  """

  short_names = {
    "description": "d",
    "value": "v"
  }

  def __getitem__(self, key):
    if key in self.short_names:
      return self.get(self.short_names[key])
    return self.get(key)

  def __setitem__(self, key, value):
    if key in self.short_names:
      key = self.short_names[key]
    dict.__setitem__(self, key, value)


class ShortNamesCollection(Collection):
  document_class = ShortNamesDocument


def test_shortnames(db):
  db.test_shortnames.drop()
  SN = ShortNamesCollection(collection=db.test_shortnames)

  doc = SN({"regular": "1"})
  doc.save()

  docs = list(SN.find())
  print docs
  assert len(docs) == 1
  assert docs[0]["regular"] == "1"

  docs[0]["value"] = "2"
  docs[0].save()

  docs = list(SN.find())
  print docs
  print dict(docs[0])
  assert len(docs) == 1
  assert docs[0]["value"] == "2"
  assert docs[0]["v"] == "2"

  # Bypass mongokat to see the real document
  raw_docs = list(db.test_shortnames.find())
  assert len(raw_docs) == 1
  assert "value" not in raw_docs[0]
  assert raw_docs[0]["v"] == "2"
