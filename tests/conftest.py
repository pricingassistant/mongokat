import pytest
from pymongo import MongoClient

import sys
sys.path.append(".")
import sample_models


@pytest.fixture(scope="function")
def client(request):
    return MongoClient("mongodb://127.0.0.1:27017")


@pytest.fixture(scope="function")
def db(request):
    return MongoClient("mongodb://127.0.0.1:27017").test


@pytest.fixture(scope="function")
def Sample(request, db):
    db.sample.drop()
    return sample_models.SampleCollection(collection=db.sample)


@pytest.fixture(scope="function")
def WithHooks(request, db):
    db.sample.drop()
    return sample_models.WithHooksCollection(collection=db.sample)
