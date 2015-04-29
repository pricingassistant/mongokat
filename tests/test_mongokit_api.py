#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2009-2011, Nicolas Clairon
# All rights reserved.
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the University of California, Berkeley nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE REGENTS AND CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

#
# This test was imported from MongoKit to provide as much API compatibility as possible
# https://raw.githubusercontent.com/namlook/mongokit/master/tests/test_api.py
#


from bson.objectid import ObjectId
from pymongo import ReadPreference
import pytest
from mongokat import Document as MongoKatDocument
from mongokat import Collection as MongoKatCollection
from mongokat.exceptions import MultipleResultsFound
from pymongo.errors import OperationFailure

SchemaDocument = MongoKatCollection
Document = MongoKatCollection
import re
from pymongo import MongoClient as Connection


class TestMongokitApi:

    @pytest.fixture(autouse=True)
    def setup(self, request, db):
        self.col = db.mongokit
        self.connection = db.client

        self.col.drop()

        def register(models):
            if not isinstance(models, list):
                models = [models]
            for m in models:
                classname = re.sub(r"^.*\.([\w]+)\'.*$", "\\1", str(m))
                setattr(self.col, classname, m(collection=self.col))

        setattr(self.connection, "register", register)

    def assertEqual(self, a, b):
        assert a == b

    def assertEquals(self, a, b):
        assert a == b

    def assertRaises(self, ExpectedException, func, exp=None):
        pytest.raises(ExpectedException, func)

    #
    #
    # Tests should be mostly untouched from here
    #
    #

    def test_save(self):
        class MyDoc(Document):
            structure = {
                "bla":{
                    "foo":unicode,
                    "bar":int,
                },
                "spam":[],
            }
        self.connection.register([MyDoc])
        mydoc = self.col.MyDoc()
        mydoc["bla"]["foo"] = u"bar"
        mydoc["bla"]["bar"] = 42
        mydoc.save()
        assert isinstance(mydoc['_id'], ObjectId)

        saved_doc = self.col.find_one({"bla.bar":42})
        for key, value in mydoc.iteritems():
            assert saved_doc[key] == value

        mydoc = self.col.MyDoc()
        mydoc["bla"]["foo"] = u"bar"
        mydoc["bla"]["bar"] = 43
        mydoc.save(uuid=True)
        assert isinstance(mydoc['_id'], unicode)
        assert mydoc['_id'].startswith("MyDoc"), mydoc['_id']

        saved_doc = self.col.find_one({"bla.bar":43})
        for key, value in mydoc.iteritems():
            assert saved_doc[key] == value

    def test_save_without_collection(self):
        return pytest.skip()

        class MyDoc(Document):
            structure = {
                "foo":int,
            }
        self.connection.register([MyDoc])
        mydoc = MyDoc()
        mydoc["foo"] = 1
        self.assertRaises(ConnectionError, mydoc.save)

    def test_delete(self):
        class MyDoc(Document):
            structure = {
                "foo":int,
            }
        self.connection.register([MyDoc])
        mydoc = self.col.MyDoc()
        mydoc['_id'] = 'foo'
        mydoc["foo"] = 1
        mydoc.save()
        assert self.col.MyDoc.find().count() == 1
        mydoc = self.col.MyDoc.get_from_id('foo')
        assert mydoc['foo'] == 1
        mydoc.delete()
        assert self.col.MyDoc.find().count() == 0

    def test_generate_skeleton(self):
        class A(SchemaDocument):
            structure = {
                "a":{"foo":int},
                "bar":unicode
            }
        self.connection.register([A])
        a = self.col.A(gen_skel=False)
        assert a == {}
        a.generate_skeleton()
        assert a == {"a":{"foo":None}, "bar":None}, a

    def test_generate_skeleton2(self):
        class A(SchemaDocument):
            structure = {
                "a":{"foo":[int]},
                "bar":{unicode:{"egg":int}}
            }
        self.connection.register([A])
        a = self.col.A(gen_skel=False)
        assert a == {}
        a.generate_skeleton()
        assert a == {"a":{"foo":[]}, "bar":{}}, a

    def test_generate_skeleton3(self):
        class A(SchemaDocument):
            structure = {
                "a":{"foo":[int], "spam":{"bla":unicode}},
                "bar":{unicode:{"egg":int}}
            }
        self.connection.register([A])
        a = self.col.A(gen_skel=False)
        assert a == {}
        a.generate_skeleton()
        assert a == {"a":{"foo":[], "spam":{"bla":None}}, "bar":{}}, a

    def test_get_from_id(self):
        class MyDoc(Document):
            structure = {
                "foo":int,
            }
        self.connection.register([MyDoc])
        mydoc = self.col.MyDoc()
        mydoc["_id"] = "bar"
        mydoc["foo"] = 3
        mydoc.save()
        fetched_doc = self.col.MyDoc.get_from_id("bar")
        assert mydoc == fetched_doc
        assert callable(fetched_doc) is False
        assert isinstance(fetched_doc, self.col.MyDoc.document_class)
        raw_doc = self.col.find_one({"_id": 'bar'})
        assert mydoc == raw_doc
        assert not isinstance(raw_doc, self.col.MyDoc.document_class)

    def test_find(self):
        class MyDoc(Document):
            structure = {
                "foo":int,
                "bar":{"bla":int},
            }
        self.connection.register([MyDoc])
        for i in range(10):
            mydoc = self.col.MyDoc()
            mydoc["foo"] = i
            mydoc["bar"]['bla'] = i
            mydoc.save()
        for i in self.col.MyDoc.find({"foo":{"$gt":4}}):
            assert isinstance(i, self.col.MyDoc.document_class), (i, type(i))
        docs_list = [i["foo"] for i in self.col.MyDoc.find({"foo":{"$gt":4}})]
        assert docs_list == [5,6,7,8,9]
        # using limit/count
        assert self.col.MyDoc.find().count() == 10, self.col.MyDoc.find().count()
        assert self.col.MyDoc.find().limit(1).count() == 10, self.col.MyDoc.find().limit(1).count()
        assert self.col.MyDoc.find().where('this.foo').count() == 9 #{'foo':0} is not taken
        assert self.col.MyDoc.find().where('this.bar.bla').count() == 9 #{'foo':0} is not taken
        assert self.col.MyDoc.find().hint([('foo', 1)])
        assert [i['foo'] for i in self.col.MyDoc.find().sort('foo', -1)] == [9,8,7,6,5,4,3,2,1,0]
        allPlans = self.col.MyDoc.find().explain()['allPlans']
        allPlans[0].pop(u'indexBounds', None)
        allPlans[0].pop(u'indexOnly', None)
        allPlans[0].pop(u'nChunkSkips', None)
        allPlans[0].pop(u'scanAndOrder', None)
        allPlans[0].pop(u'isMultiKey', None)

        allPlans[0].pop(u'bar', None)
        allPlans[0].pop(u'foo', None)

        self.assertEqual(
            allPlans,
            [
                {
                    u'cursor': u'BasicCursor',
                    u'nscannedObjects': 10,
                    u'nscanned': 10,
                    u'n': 10,
                },
            ],
        )
        next_doc =  self.col.MyDoc.find().sort('foo',1).next()
        assert callable(next_doc) is False
        assert isinstance(next_doc, self.col.MyDoc.document_class)
        assert next_doc['foo'] == 0
        assert len(list(self.col.MyDoc.find().skip(3))) == 7, len(list(self.col.MyDoc.find().skip(3)))
        from pymongo.cursor import Cursor
        assert isinstance(self.col.MyDoc.find().skip(3), Cursor)

    def test_find_one(self):
        class MyDoc(Document):
            structure = {
                "foo":int
            }
        self.connection.register([MyDoc])
        assert self.col.MyDoc.find_one() is None
        mydoc = self.col.MyDoc()
        mydoc['foo'] = 0
        mydoc.save()
        mydoc = self.col.MyDoc.find_one()
        assert mydoc["foo"] == 0
        assert isinstance(mydoc, self.col.MyDoc.document_class)
        for i in range(10):
            mydoc = self.col.MyDoc()
            mydoc["foo"] = i
            mydoc.save()
        one_doc = self.col.MyDoc.find_one()
        assert callable(one_doc) is False
        raw_mydoc = self.col.find_one()
        assert one_doc == raw_mydoc

    def test_find_and_modify_query_fails(self):
        class MyDoc(Document):
            structure = {
                "baz":int
            }
        self.connection.register([MyDoc])
        assert self.col.MyDoc.find_and_modify(query={"baz": 1}, update={"$set": {"baz": 2}}) is None

    def test_find_and_modify_query_succeeds(self):
        class MyDoc(Document):
            structure = {
                "baz":int
            }
        self.connection.register([MyDoc])
        mydoc = self.col.MyDoc()
        mydoc["baz"] = 1
        mydoc.save()

        mydoc = self.col.MyDoc.find_and_modify(query={"baz": 1}, update={"$set": {"baz": 2}}, new=True)
        assert isinstance(mydoc, self.col.MyDoc.document_class)
        self.assertEquals(2, mydoc["baz"])

    def test_one(self):
        class MyDoc(Document):
            structure = {
                "foo":int
            }
        self.connection.register([MyDoc])
        mydoc = self.col.MyDoc()
        mydoc['foo'] = 0
        mydoc.save()
        # raw_mydoc = self.col.one()
        mydoc = self.col.MyDoc.one()
        assert callable(mydoc) is False
        # assert mydoc == raw_mydoc
        assert mydoc["foo"] == 0
        assert isinstance(mydoc, self.col.MyDoc.document_class)
        for i in range(10):
            mydoc = self.col.MyDoc()
            mydoc["foo"] = i
            mydoc.save()
        self.assertRaises(MultipleResultsFound, self.col.MyDoc.one)
        #self.assertRaises(MultipleResultsFound, self.col.one)

    def test_find_random(self):
        class MyDoc(Document):
            structure = {
                "foo":int
            }
        self.connection.register([MyDoc])
        # assert self.col.find_random() is None
        assert self.col.MyDoc.find_random() is None
        for i in range(50):
            mydoc = self.col.MyDoc()
            mydoc["foo"] = i
            mydoc.save()
        # raw_mydoc = self.col.find_random()
        mydoc = self.col.MyDoc.find_random()
        assert callable(mydoc) is False
        assert isinstance(mydoc, self.col.MyDoc.document_class)
        # assert mydoc != raw_mydoc, (mydoc, raw_mydoc)

    def test_fetch(self):
        class DocA(Document):
            structure = {
                "doc_a":{'foo':int},
            }
        self.connection.register([DocA])
        class DocB(Document):
            structure = {
                "doc_b":{"bar":int},
            }
        self.connection.register([DocB])
        # creating DocA
        for i in range(10):
            mydoc = self.col.DocA()
            mydoc['doc_a']["foo"] = i
            mydoc.save()
        # creating DocB
        for i in range(5):
            mydoc = self.col.DocB()
            mydoc['doc_b']["bar"] = i
            mydoc.save()

        # all get all documents present in the collection (ie: 15 here)
        assert self.col.DocA.find().count() == 15

        # fetch get only the corresponding documents:
        assert self.col.DocA.fetch().count() == 10, self.col.DocA.fetch().count()
        assert self.col.DocB.fetch().count() == 5

        index = 0
        for doc in self.col.DocA.fetch():
            assert doc == {'_id':doc['_id'], 'doc_a':{'foo':index}}, doc
            assert callable(doc) is False
            index += 1

        #assert DocA.fetch().limit(12).count() == 10, DocA.fetch().limit(1).count() # ???
        assert self.col.DocA.fetch().where('this.doc_a.foo > 3').count() == 6

    def test_fetch_with_query(self):
        class DocA(Document):
            structure = {
                "bar":unicode,
                "doc_a":{'foo':int},
            }
        class DocB(Document):
            structure = {
                "bar":unicode,
                "doc_b":{"bar":int},
            }
        self.connection.register([DocA, DocB])

        # creating DocA
        for i in range(10):
            mydoc = self.col.DocA()
            if i % 2 == 0:
                mydoc['bar'] = u"spam"
            else:
                mydoc['bar'] = u"egg"
            mydoc['doc_a']["foo"] = i
            mydoc.save()
        # creating DocB
        for i in range(5):
            mydoc = self.col.DocB()
            if i % 2 == 0:
                mydoc['bar'] = u"spam"
            else:
                mydoc['bar'] = u"egg"
            mydoc['doc_b']["bar"] = i
            mydoc.save()

        # all get all documents present in the collection (ie: 15 here)
        assert self.col.DocA.find().count() == 15
        assert self.col.DocA.fetch().count() == 10, self.col.DocA.fetch().count()
        assert self.col.DocB.fetch().count() == 5

        assert self.col.DocA.fetch({'bar':'spam'}).count() == 5
        assert self.col.DocB.fetch({'bar':'spam'}).count() == 3

    def test_fetch_inheritance(self):
        return pytest.skip("No inheritance for structures")
        class Doc(Document):
            structure = {
                "doc":{'bla':int},
            }
        class DocA(Doc):
            structure = {
                "doc_a":{'foo':int},
            }
        class DocB(DocA):
            structure = {
                "doc_b":{"bar":int},
            }
        self.connection.register([Doc, DocA, DocB])
        # creating DocA
        for i in range(10):
            mydoc = self.col.DocA()
            mydoc['doc']["bla"] = i+1
            mydoc['doc_a']["foo"] = i
            mydoc.save()
        # creating DocB
        for i in range(5):
            mydoc = self.col.DocB()
            mydoc['doc']["bla"] = i+1
            mydoc['doc_a']["foo"] = i
            mydoc['doc_b']["bar"] = i+2
            mydoc.save()

        # all get all documents present in the collection (ie: 15 here)
        assert self.col.DocA.find().count() == 15

        # fetch get only the corresponding documents:
        # DocB is a subclass of DocA and have all fields of DocA so
        # we get all doc here
        assert self.col.DocA.fetch().count() == 15, self.col.DocA.fetch().count()
        # but only the DocB as DocA does not have a 'doc_a' field
        assert self.col.DocB.fetch().count() == 5
        index = 0
        for doc in self.col.DocB.fetch():
            assert doc == {'_id':doc['_id'], 'doc_a':{'foo':index}, 'doc':{'bla':index+1}, "doc_b":{'bar':index+2}}, (doc, index)
            index += 1

        #assert DocA.fetch().limit(12).count() == 10, DocA.fetch().limit(1).count() # ???
        assert self.col.DocA.fetch().where('this.doc_a.foo > 3').count() == 7

    def test_fetch_one(self):
        class DocA(Document):
            structure = {
                "doc_a":{'foo':int},
            }
        class DocB(DocA):
            structure = {
                "doc_a":{"bar":int},
            }
        self.connection.register([DocA, DocB])

        # creating DocA
        mydoc = self.col.DocA()
        mydoc['doc_a']["foo"] = 1
        mydoc.save()
        # creating DocB
        mydoc = self.col.DocB()
        mydoc['doc_a']["bar"] = 2
        mydoc.save()

        # docb = self.col.DocB.fetch_one()
        # assert callable(docb) is False
        # assert docb
        # assert isinstance(docb, self.col.DocB.document_class)
        self.assertRaises(MultipleResultsFound, self.col.DocB.fetch_one)

    def test_query_with_passing_collection(self):
        class MyDoc(Document):
            structure = {
                'foo':int,
            }
        self.connection.register([MyDoc])

        mongokit = self.connection.test.mongokit
        mongokit.MyDoc = self.col.MyDoc

        # boostraping
        for i in range(10):
            mydoc = mongokit.MyDoc()
            mydoc['_id'] = unicode(i)
            mydoc['foo'] = i
            mydoc.save()

        # get_from_id
        fetched_doc = mongokit.MyDoc.get_from_id('4')
        assert fetched_doc.collection == mongokit

        # all
        fetched_docs = mongokit.MyDoc.find({'foo':{'$gt':2}})
        assert fetched_docs.count() == 7
        for doc in fetched_docs:
            assert doc.collection == mongokit

        # one
        doc = mongokit.MyDoc.fetch_one({'foo':2})
        assert doc.collection == mongokit

        # fetch
        fetched_docs = mongokit.MyDoc.fetch({'foo':{'$gt':2}})
        assert fetched_docs.count() == 7
        for doc in fetched_docs:
            assert doc.collection == mongokit

        # fetch_one
        doc = mongokit.MyDoc.fetch_one({'foo':2})
        assert doc.collection == mongokit

    def test_skip_validation(self):
        return pytest.skip("no validation")
        class DocA(Document):
            structure = {
                "doc_a":{'foo':int},
            }
        self.connection.register([DocA])

        # creating DocA
        mydoc = self.col.DocA()
        mydoc['doc_a']["foo"] = u'bar'
        assertion = False
        try:
            mydoc.save()
        except SchemaTypeError:
            assertion = True
        assert assertion
        mydoc.save(validate=False)

        DocA.skip_validation = True

        # creating DocA
        mydoc = self.col.DocA()
        mydoc['doc_a']["foo"] = u'foo'
        self.assertRaises(SchemaTypeError, mydoc.save, validate=True)
        mydoc.save()


    def test_connection(self, client):
        class DocA(Document):
            structure = {
                "doc_a":{'foo':int},
            }
        self.connection.register([DocA])
        assertion = True
        try:
            DocA.connection
        except AttributeError:
            assertion = True
        assert assertion
        try:
            DocA.db
        except AttributeError:
            assertion = True
        assert assertion
        try:
            DocA.collection
        except AttributeError:
            assertion = True
        assert assertion

        assert str(self.col.DocA.connection) == str(client)
        assert str(self.col.DocA.collection) == str(client['test']['mongokit'])
        assert str(self.col.DocA.db) == str(client['test'])

    def test_all_with_dynamic_collection(self):
        return pytest.skip("Nope")
        class Section(Document):
            structure = {"section":int}
        self.connection.register([Section])

        s = self.connection.test.section.Section()
        s['section'] = 1
        s.save()

        s = self.connection.test.section.Section()
        s['section'] = 2
        s.save()

        s = self.connection.test.other_section.Section()
        s['section'] = 1
        s.save()

        s = self.connection.test.other_section.Section()
        s['section'] = 2
        s.save()


        sect_col = self.connection.test.section
        sects = [s.collection.name == 'section' and s.db.name == 'test' for s in sect_col.Section.find({})]
        assert len(sects) == 2, len(sects)
        assert any(sects)
        sects = [s.collection.name == 'section' and s.db.name == 'test' for s in sect_col.Section.fetch()]
        assert len(sects) == 2
        assert any(sects)

        sect_col = self.connection.test.other_section
        sects = [s.collection.name == 'other_section' and s.db.name == 'test' for s in sect_col.Section.find({})]
        assert len(sects) == 2
        assert any(sects)
        sects = [s.collection.name == 'other_section' and s.db.name == 'test' for s in sect_col.Section.fetch()]
        assert len(sects) == 2
        assert any(sects)

    def test_get_collection_with_connection(self):
        return pytest.skip("Nope")
        class Section(Document):
            structure = {"section":int}
        connection = Connection('localhost')
        connection.register([Section])
        col = connection.test.mongokit
        assert col.database.connection == col.Section.connection
        assert col.database.name == 'test' == col.Section.db.name
        assert col.name == 'mongokit' == col.Section.collection.name

    def test_get_size(self):
        class MyDoc(Document):
            structure = {
                "doc":{"foo":int, "bla":unicode},
            }
        self.connection.register([MyDoc])

        mydoc = self.col.MyDoc()
        mydoc['doc']['foo'] = 3
        mydoc['doc']['bla'] = u'bla bla'
        assert mydoc.get_size() == 41, mydoc.get_size()

        mydoc['doc']['bla'] = u'bla bla'+'b'*12
        assert mydoc.get_size() == 41+12

        # validate() disabled for now!
        return

        mydoc.validate()

        mydoc['doc']['bla'] = u'b'*40000000
        self.assertRaises(MaxDocumentSizeError, mydoc.validate)

    def test_get_with_no_wrap(self):
        class MyDoc(Document):
            structure = {"foo":int}
        self.connection.register([MyDoc])

        for i in xrange(20):
            mydoc = self.col.MyDoc()
            mydoc['foo'] = i
            mydoc.save()

        import time
        start = time.time()
        wrapped_mydocs = [i for i in self.col.MyDoc.find()]
        end = time.time()
        wrap_time = end-start

        start = time.time()
        mydocs = [i for i in self.col.find().sort('foo', -1)]
        end = time.time()
        no_wrap_time = end-start

        # Had to comment this because we got really fast! :)
        # assert no_wrap_time < wrap_time

        assert isinstance(wrapped_mydocs[0], self.col.MyDoc.document_class)
        assert not isinstance(mydocs[0], MyDoc), type(mydocs[0])
        assert [i['foo'] for i in mydocs] == list(reversed(range(20))), [i['foo'] for i in mydocs]
        assert mydocs[0]['foo'] == 19, mydocs[0]['foo']

        assert not isinstance(self.col.find().sort('foo', -1).next(), self.col.MyDoc.document_class)

    def test_get_dbref(self):
        return pytest.skip("no dbref")
        class MyDoc(Document):
            structure = {"foo":int}
        self.connection.register([MyDoc])

        mydoc = self.col.MyDoc()
        mydoc['_id'] = u'1'
        mydoc['foo'] = 1
        mydoc.save()

        mydoc = self.connection.test.othercol.MyDoc()
        mydoc['_id'] = u'2'
        mydoc['foo'] = 2
        mydoc.save()

        mydoc = self.connection.othertest.mongokit.MyDoc()
        mydoc['_id'] = u'3'
        mydoc['foo'] = 3
        mydoc.save()

        mydoc = self.col.MyDoc.find_one({'foo':1})
        assert mydoc.get_dbref(), DBRef(u'mongokit', u'1', u'test')

        mydoc = self.connection.test.othercol.MyDoc.find_one({'foo':2})
        assert mydoc.get_dbref() == DBRef(u'othercol', u'2', u'test')

        mydoc = self.connection.othertest.mongokit.MyDoc.find_one({'foo':3})
        assert mydoc.get_dbref() == DBRef(u'mongokit', u'3', u'othertest')

    def test__hash__(self):
        class MyDoc(Document):
            structure = {"foo":int}
        self.connection.register([MyDoc])

        mydoc = self.col.MyDoc()
        mydoc['foo'] = 1
        self.assertRaises(TypeError, hash, mydoc)

        mydoc.save()
        hash(mydoc)

    def test_non_callable(self):
        class MyDoc(Document):
            structure = {"foo":int}
        self.connection.register([MyDoc])
        mydoc = self.col.MyDoc()
        self.assertRaises(TypeError, mydoc)
        assert callable(mydoc) is False


    def test_bad_call(self):
        return pytest.skip()
        class MyDoc(Document):
            structure = {"foo":int}
        self.assertRaises(TypeError, self.connection.test.col.MyDoc)
        self.connection.register([MyDoc])
        self.connection.test.col.MyDoc()
        self.assertRaises(TypeError, self.connection.test.col.Bla)
        self.assertRaises(TypeError, self.connection.test.Bla)


    def test_fetched_dot_notation(self):
        return pytest.skip("No dot notation")
        class MyDoc(Document):
            use_dot_notation = True
            structure = {
                "foo":int,
                "bar":{"egg":unicode},
                "toto":{"spam":{"bla":int}}
            }

        self.connection.register([MyDoc])
        mydoc = self.col.MyDoc()
        mydoc.foo = 3
        mydoc.bar.egg = u'bla'
        mydoc.toto.spam.bla = 7
        mydoc.save()
        fetched_doc = self.col.MyDoc.find_one()
        assert fetched_doc.foo == 3, fetched_doc.foo
        assert fetched_doc.bar.egg == "bla", fetched_doc.bar.egg
        self.assertEqual(fetched_doc.toto.spam.bla, 7)


    def test_validate_doc_with_field_added_after_save(self):
        return pytest.skip("no validation")
        class Doc(Document):
           structure = {
               "foo": unicode,
           }
        self.connection.register([Doc])

        doc = self.col.Doc()
        doc['foo'] = u"bla"
        doc.save()
        doc['bar'] = 2
        self.assertRaises(StructureError, doc.validate)

    def test_distinct(self):
        class Doc(Document):
            structure = {
                "foo": unicode,
                "bla": int
            }
        self.connection.register([Doc])

        for i in range(15):
            if i % 2 == 0:
                foo = u"blo"
            else:
                foo = u"bla"
            doc = self.col.Doc(doc={'foo':foo, 'bla':i})
            doc.save()
        assert self.col.find().distinct('foo') == ['blo', 'bla']
        assert self.col.find().distinct('bla') == range(15)

    def test_explain(self):
        return pytest.skip()
        class MyDoc(Document):
            structure = {
                "foo":int,
                "bar":{"bla":int},
            }
        self.connection.register([MyDoc])
        for i in range(10):
            mydoc = self.col.MyDoc()
            mydoc["foo"] = i
            mydoc["bar"]['bla'] = i
            mydoc.save()
        explain1 = self.col.MyDoc.find({"foo":{"$gt":4}}).explain()
        explain2 = self.col.find({'foo':{'gt':4}}).explain()
        explain1.pop('n')
        explain2.pop('n')
        explain1['allPlans'][0].pop('n')
        explain1.pop('stats', None)
        explain2['allPlans'][0].pop('n')
        explain2.pop('stats', None)
        self.assertEqual(explain1, explain2)

    def test_with_long(self):
        return pytest.skip("No operators")
        class Doc(Document):
            structure = {
                "foo":OR(int, long),
                "bar":unicode,
            }
        self.connection.register([Doc])
        doc = self.col.Doc()
        doc['foo'] = 12L
        doc.save()
        fetch_doc = self.col.Doc.find_one()
        fetch_doc['bar'] = u'egg'
        fetch_doc.save()

    def test_skip_validation_with_required_field(self):
        return pytest.skip("no validation")
        class Task(Document):
            structure = {
                'extra' : unicode,
            }
            required_fields = ['extra']
            skip_validation = True
        self.connection.register([Task])
        task = self.col.Task()
        task['extra'] = u'foo'
        task.validate()

    def test_passing_collection_in_argument(self):
        return pytest.skip("nope")
        class MyDoc(Document):
            structure = {
                'foo':unicode
            }
        doc = MyDoc(collection=self.col)
        doc['foo'] = u'bla'
        doc.save()

    def test_reload(self):
        class MyDoc(Document):
            structure = {
                'foo':{
                    'bar':unicode,
                    'eggs':{'spam':int},
                },
                'bla':unicode
            }
        self.connection.register([MyDoc])

        doc = self.col.MyDoc()
        self.assertRaises(KeyError, doc.reload)
        doc['_id'] = 3
        # doc['foo'] = {'eggs': {}}
        doc['foo']['bar'] = u'mybar'
        doc['foo']['eggs']['spam'] = 4
        doc['bla'] = u'ble'
        self.assertRaises(OperationFailure, doc.reload)
        doc.save()

        assert doc == {'_id': 3, 'foo': {u'eggs': {u'spam': 4}, u'bar': u'mybar'}, 'bla': u'ble'}

        doc['bla'] = u'bli'

        self.col.update({'_id':doc['_id']}, {'$set':{'foo.eggs.spam':2}})

        print "******" * 20
        print

        self.col.MyDoc.gen_skel = False
        doc2 = self.col.MyDoc.find_one({'_id':doc['_id']})
        print doc2
        assert doc2 == {'_id': 3, 'foo': {u'eggs': {u'spam': 2}, u'bar': u'mybar'}, 'bla': u'ble'}

        doc.reload()
        assert doc == {'_id': 3, 'foo': {u'eggs': {u'spam': 2}, u'bar': u'mybar'}, 'bla': u'ble'}

    def test_rewind(self):
        class MyDoc(Document):
            structure = {
                'foo':int,
            }
        self.connection.register([MyDoc])

        for i in range(10):
            doc = self.col.MyDoc()
            doc['foo'] = i
            doc.save()

        cur = self.col.MyDoc.find()
        for i in cur:
            assert isinstance(i, self.col.MyDoc.document_class), type(MyDoc)
        try:
            cur.next()
        except StopIteration:
            pass
        cur.rewind()
        for i in cur:
            assert isinstance(i, self.col.MyDoc.document_class), type(MyDoc)
        for i in cur.rewind():
            assert isinstance(i, self.col.MyDoc.document_class), type(MyDoc)


    def test_decorator(self):
        @self.connection.register
        class MyDoc(Document):
            structure = {
                'foo':int,
            }

        mydoc = self.col.MyDoc()
        mydoc['foo'] = 3
        mydoc.save()

        raw_doc = self.col.MyDoc.find_one()
        self.assertEqual(raw_doc['foo'], 3)
        assert isinstance(raw_doc, self.col.MyDoc.document_class)


    def test_collection_name_filled(self):
        return pytest.skip("nope")
        @self.connection.register
        class MyDoc(Document):
            __collection__ = 'mydoc'
            structure = {
                'foo':int,
            }

        mydoc = self.connection.test.MyDoc()
        mydoc['foo'] = 3
        mydoc.save()
        self.assertEqual(mydoc.collection.name, 'mydoc')

        raw_doc = self.connection.test.MyDoc.find_one()
        self.assertEqual(self.col.MyDoc.find_one(), None)
        self.assertEqual(raw_doc['foo'], 3)
        self.assertEqual(raw_doc, mydoc)
        assert isinstance(raw_doc, self.col.MyDoc.document_class)

        mydoc = self.col.MyDoc()
        mydoc['foo'] = 3
        mydoc.save()
        self.assertEqual(mydoc.collection.name, 'mongokit')

        raw_doc = self.col.MyDoc.find_one()
        self.assertEqual(raw_doc['foo'], 3)
        self.assertEqual(raw_doc, mydoc)
        assert isinstance(raw_doc, self.col.MyDoc.document_class)

    def test_database_name_filled(self):
        return pytest.skip("nope")
        failed = False
        @self.connection.register
        class MyDoc(Document):
            __database__ = 'mydoc'
            structure = {
                'foo':int,
            }
        try:
            doc = self.connection.MyDoc()
        except AttributeError, e:
            failed = True
            self.assertEqual(str(e), 'MyDoc: __collection__ attribute not '
              'found. You cannot specify the `__database__` attribute '
              'without the `__collection__` attribute')
        self.assertEqual(failed, True)

        @self.connection.register
        class MyDoc(Document):
            __database__ = 'test'
            __collection__ = 'mydoc'
            structure = {
                'foo':int,
            }

        # test directly from a connection
        mydoc = self.connection.MyDoc()
        mydoc['foo'] = 3
        mydoc.save()
        self.assertEqual(mydoc.collection.name, 'mydoc')
        self.assertEqual(mydoc.collection.database.name, 'test')
        self.assertEqual(self.col.MyDoc.find_one(), None)

        raw_doc = self.connection.MyDoc.find_one()
        self.assertEqual(raw_doc['foo'], 3)
        self.assertEqual(raw_doc, mydoc)
        assert isinstance(raw_doc, self.col.MyDoc.document_class)

        # test directly from a database
        mydoc = self.connection.othertest.MyDoc()
        mydoc['foo'] = 3
        mydoc.save()
        self.assertEqual(mydoc.collection.name, 'mydoc')
        self.assertEqual(mydoc.collection.database.name, 'othertest')
        self.assertEqual(self.col.MyDoc.find_one(), None)

        raw_doc = self.connection.othertest.MyDoc.find_one()
        self.assertEqual(raw_doc['foo'], 3)
        self.assertEqual(raw_doc, mydoc)
        assert isinstance(raw_doc, self.col.MyDoc.document_class)

        # and still can use it via a collection
        mydoc = self.col.MyDoc()
        mydoc['foo'] = 3
        mydoc.save()
        self.assertEqual(mydoc.collection.name, 'mongokit')
        self.assertEqual(mydoc.collection.database.name, 'test')

        raw_doc = self.col.MyDoc.find_one()
        self.assertEqual(raw_doc['foo'], 3)
        self.assertEqual(raw_doc, mydoc)
        assert isinstance(raw_doc, self.col.MyDoc.document_class)


    def test_no_collection_in_virtual_document(self):
        return pytest.skip("nope")
        @self.connection.register
        class Root(Document):
            __database__ = "test"

        @self.connection.register
        class DocA(Root):
           __collection__ = "doca"
           structure = {'title':unicode}

        doc = self.connection.DocA()
        doc['title'] = u'foo'
        doc.save()

        self.assertEqual(self.connection.test.doca.find_one(), doc)


    def test_basestring_type(self):
        return pytest.skip("nope")
        @self.connection.register
        class DocA(Document):
           __database__ = 'test'
           __collection__ = "doca"
           structure = {'title':unicode}

        doc = self.connection.DocA()
        doc['title'] = 'foo'
        failed = False
        try:
            doc.save()
        except SchemaTypeError, e:
            self.assertEqual(str(e), "title must be an instance of unicode not str")
            failed = True
        self.assertEqual(failed, True)

        @self.connection.register
        class DocA(Document):
           __database__ = 'test'
           __collection__ = "doca"
           authorized_types = Document.authorized_types+[str]
           structure = {'title':str}

        doc = self.connection.DocA()
        doc['title'] = u'foo'
        failed = False
        try:
            doc.save()
        except SchemaTypeError, e:
            self.assertEqual(str(e), "title must be an instance of str not unicode")
            failed = True
        self.assertEqual(failed, True)


        @self.connection.register
        class DocA(Document):
           __database__ = 'test'
           __collection__ = "doca"
           structure = {'title':basestring}

        doc = self.connection.DocA()
        doc['title'] = u'foo'
        doc.save()
        doc['title'] = 'foo'
        doc.save()

        self.assertEqual(self.connection.test.doca.find_one(), doc)

    def test_float_and_int_types(self):
        return pytest.skip("nope")
        @self.connection.register
        class DocA(Document):
           __database__ = 'test'
           __collection__ = "doca"
           structure = {'foo':int}

        doc = self.connection.DocA()
        doc['foo'] = 3.0
        failed = False
        try:
            doc.save()
        except SchemaTypeError, e:
            self.assertEqual(str(e), "foo must be an instance of int not float")
            failed = True
        self.assertEqual(failed, True)

        @self.connection.register
        class DocA(Document):
           __database__ = 'test'
           __collection__ = "doca"
           authorized_types = Document.authorized_types+[str]
           structure = {'foo':float}

        doc = self.connection.DocA()
        doc['foo'] = 2
        failed = False
        try:
            doc.save()
        except SchemaTypeError, e:
            self.assertEqual(str(e), "foo must be an instance of float not int")
            failed = True
        self.assertEqual(failed, True)


        @self.connection.register
        class DocA(Document):
           __database__ = 'test'
           __collection__ = "doca"
           structure = {'foo':OR(int, float)}

        doc = self.connection.DocA()
        doc['foo'] = 3
        doc.save()
        doc['foo'] = 2.0
        doc.save()

        self.assertEqual(self.connection.test.doca.find_one(), doc)

    def test_cursor_slicing(self):
        @self.connection.register
        class DocA(Document):
            structure = {'foo':int}

        for i in range(10):
            doc = self.col.DocA()
            doc['foo'] = i
            doc.save()

        self.assertEqual(isinstance(self.col.DocA.find()[0], self.col.DocA.document_class), True)
        self.assertEqual(isinstance(self.col.DocA.find()[3], self.col.DocA.document_class), True)
        self.assertEqual(isinstance(self.col.DocA.find()[3:], self.col.DocA.find().__class__), True)

    def test_unwrapped_cursor(self):

        self.assertEqual(self.col.count(), 0)

        doc_id = self.col.save({}, w=1)
        self.assertEqual(self.col.count(), 1)

        self.col.find({"_id":doc_id})[0]

    def test_pass_connection_arguments_to_cursor(self):
        return pytest.skip()
        class MyDoc(Document):
            structure = {
                "foo":int,
                "bar":{"bla":int},
            }
        con = Connection(read_preference=ReadPreference.SECONDARY_PREFERRED,
            secondary_acceptable_latency_ms=16)
        con.register([MyDoc])
        col = con['test']['mongokit']
        assert col.MyDoc.find()._Cursor__read_preference == ReadPreference.SECONDARY_PREFERRED
        assert col.MyDoc.find()._Cursor__secondary_acceptable_latency_ms == 16
        con.close()