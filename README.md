MongoKat
========

[![Build Status](https://travis-ci.org/pricingassistant/mongokat.svg?branch=master)](https://travis-ci.org/pricingassistant/mongokat) [![MIT License](https://img.shields.io/github/license/pricingassistant/mongokat.svg)](LICENSE)

MongoKat is a minimalist MongoDB ORM/ODM, inspired by the "hands off" API of [MongoKit](https://github.com/namlook/mongokit).

See http://mongokat.readthedocs.org/ for documentation, code samples and API reference.

Tests
=====

You can just do `make test` to run the tests after setting up your environment (`make virtualenv` might help)

Alternatively, you can use `make docker_test` to run tests inside a Docker image, without worrying about installing MongoDB on your machine.

Contributing
============

We'll be happy to review any pull requests!

TODO
====

See the GitHub issues for a list of the features we'd like to add!

Docs
====

To edit the docs with livereload:

```
cd docs
make serve
```

Credits
=======

 - [MongoKit](https://github.com/namlook/mongokit), for the inspiration and part of the code
 - [PyMongo](https://github.com/mongodb/mongo-python-driver)
