from mongokat import Collection, Document


class SampleDocument(Document):
    def my_method(self):
        return 1


class SampleCollection(Collection):
    document_class = SampleDocument


GLOBAL_HOOK_HISTORY = []


class WithHooksDocument(Document):

    def before_delete(self, **kwargs):
        GLOBAL_HOOK_HISTORY.append(["before_delete", self["a"]])

    def after_delete(self, **kwargs):
        GLOBAL_HOOK_HISTORY.append(["after_delete", self["a"]])

    def after_save(self, **kwargs):
        GLOBAL_HOOK_HISTORY.append(["after_save", self["a"]])


class WithHooksCollection(Collection):
    document_class = WithHooksDocument
