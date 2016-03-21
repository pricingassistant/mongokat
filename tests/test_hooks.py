from . import sample_models


def assert_hooks(hooks):
    assert sample_models.GLOBAL_HOOK_HISTORY == hooks
    sample_models.GLOBAL_HOOK_HISTORY = []


def test_document_hook_save(WithHooks):

    assert_hooks([])

    assert WithHooks.count() == 0

    assert_hooks([])

    WithHooks.insert_one({"a": 1})
    a1 = WithHooks.find_one()

    assert_hooks([["after_save", 1]])

    a1["b"] = 2
    a1.save()

    assert_hooks([["before_save", 1], ["after_save", 1]])

    a1 = WithHooks.find_one()
    a1["a"] = 2
    a1.save()

    assert_hooks([["before_save", 1], ["after_save", 2]])

    try:
        a1.save_partial({"a": 3, "raise_before_save": True})
    except:
        assert_hooks([])
        assert a1["a"] == 2
    else:
        assert False

    try:
        a1.unset_fields(["a", "raise_before_save"])
    except:
        assert_hooks([])
        assert a1.get("a") == 2
    else:
        assert False

    WithHooks.update({}, {"$set": {"a": 3}})

    assert_hooks([["before_save", 2], ["after_save", 3]])

    # Default = before
    WithHooks.find_one_and_update({}, {"$set": {"a": 4}})
    assert_hooks([["before_save", 3], ["after_save", 3]])

    WithHooks.find_one_and_update({}, {"$set": {"a": 5}}, return_document="before")
    assert_hooks([["before_save", 4], ["after_save", 4]])

    WithHooks.find_one_and_update({}, {"$set": {"a": 6}}, return_document="after")
    assert_hooks([["before_save", 5], ["after_save", 6]])

    WithHooks.update_one({}, {"$set": {"a": 7}})
    assert_hooks([["before_save", 6], ["after_save", 7]])

    WithHooks.update_many({}, {"$set": {"a": 8}})
    assert_hooks([["before_save", 7], ["after_save", 8]])

    WithHooks.replace_one({}, {"a": 9})
    assert_hooks([["before_save", 8], ["after_save", 9]])

    WithHooks.update({}, {"$set": {"incr_before_save": True, "a": 10}})
    assert_hooks([["before_save", 9], ["after_save", 11]])

def test_document_hook_delete(WithHooks):

    assert_hooks([])

    assert WithHooks.count() == 0

    assert_hooks([])

    WithHooks.insert_one({"a": 1})
    assert_hooks([["after_save", 1]])

    WithHooks.find_one().delete()

    assert_hooks([["before_delete", 1], ["after_delete", 1]])

    WithHooks.insert_one({"a": 2})
    assert_hooks([["after_save", 2]])

    WithHooks.find_one_and_delete({})
    assert_hooks([["before_delete", 2], ["after_delete", 2]])

    WithHooks.insert_one({"a": 3})
    assert_hooks([["after_save", 3]])

    WithHooks.remove({})
    assert_hooks([["before_delete", 3], ["after_delete", 3]])

    WithHooks.insert_one({"a": 4})
    assert_hooks([["after_save", 4]])

    WithHooks.delete_one({})
    assert_hooks([["before_delete", 4], ["after_delete", 4]])

    WithHooks.insert_one({"a": 5})
    assert_hooks([["after_save", 5]])

    WithHooks.delete_many({})
    assert_hooks([["before_delete", 5], ["after_delete", 5]])

    assert WithHooks.count() == 0
