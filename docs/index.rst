MongoKat
========

`MongoKat <https://github.com/pricingassistant/mongokat>`_ is a minimalist MongoDB ORM/ODM, inspired by the "hands off" API of `MongoKit <https://github.com/namlook/mongokit>`_. It was created at `Pricing Assistant <http://www.pricingassistant.com/>`_, drawing from our experience managing a large Python codebase.

It differs from MongoKit in a few ways:

 - **Less features:** we focus on basic Collection & Document methods.
 - **Less magic:** MongoKit's use of complex Python features like ``__mro__`` and ``__metaclass__`` made bugs and memory leaks hard to debug.
 - **Cleaner design:** We enforce a separation between collection-level methods (find, aggregate, ...) and document-level methods (save, reload, ...)
 - **Better performance:** The Cursor class is not wrapped anymore so the overhead of instanciating Documents instead of dicts is now close to zero.
 - **Requires pymongo 3.0+**, taking advantage of its new features. To make transition to 3.0 easier (lots of pymongo's APIs got renamed or deprecated) MongoKat still supports some 2.x-style parameters and method names.
 - **Support for simple hooks:** ``before_delete``, ``after_delete``, ``after_save``. Useful for keeping data up-to-date in ElasticSearch for instance, on a best-effort basis (some hooks may be lost under high load when using methods like update_many).
 - **Support for protected fields** that can't be updated directly. Useful for making sure developers to use specific methods of a Document.


Installation
============

You can either clone the `code from GitHub <https://github.com/pricingassistant/mongokat>`_ or install it via pip:

```
pip install mongokat
```

Code sample
===========

.. code-block:: python

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


By the way, this is an `actual test
<https://github.com/pricingassistant/mongokat/blob/master/tests/test_readme_sample.py>`_!


Migration guide from MongoKit
=============================

First you should get familiar with the new `CRUD methods <http://api.mongodb.org/python/current/changelog.html#collection-changes>`_) from PyMongo 3.0. All of them work as expected in MongoKat.

We have generally tried to limit the changes needed for a migration to the models themselves, while the code actually using them should work without major changes.

Here is a list of things you should be aware of:

 - You will have to split your Models into Document and Collection classes. For instance, ``find()`` belongs to a Collection, whereas ``reload()`` belongs to a Document.
 - Initialization logic is different/cleaner, models are not magically registered everywhere, you have to explicitly instanciate them.
 - Structures are not inherited.


API Reference
=============

mongokat.collection.Collection
------------------------------

.. autoclass:: mongokat.collection.Collection
	:members:
	:undoc-members:

mongokat.document.Document
--------------------------

.. autoclass:: mongokat.document.Document
	:members:
	:undoc-members:


Credits
=======

 - `MongoKit <https://github.com/namlook/mongokit>`_, for the inspiration and part of the code
 - `PyMongo <https://github.com/mongodb/mongo-python-driver>`_
