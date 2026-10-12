import logging

import pytest

from app.services.vector_service import VectorService


class StubCollection:
    def __init__(self, fail_times=0):
        self.fail_times = fail_times
        self.delete_calls = 0

    def get(self, where=None, include=None):
        return {"ids": ["a", "b"]}

    def delete(self, ids=None):
        self.delete_calls += 1
        if self.delete_calls <= self.fail_times:
            raise RuntimeError("chroma down")


def _vs(collection):
    vs = VectorService.__new__(VectorService)
    vs.collection = collection
    return vs


def test_delete_document_retries_then_succeeds():
    col = StubCollection(fail_times=1)
    _vs(col).delete_document(1, 1)
    assert col.delete_calls == 2


def test_delete_document_raises_after_two_failures(caplog):
    col = StubCollection(fail_times=5)
    with caplog.at_level(logging.ERROR):
        with pytest.raises(RuntimeError, match="Vector cleanup incomplete"):
            _vs(col).delete_document(1, 1)
    assert col.delete_calls == 2
    assert any("cleanup incomplete" in r.getMessage() for r in caplog.records)


def test_delete_document_nothing_to_delete():
    class Empty(StubCollection):
        def get(self, where=None, include=None):
            return {"ids": []}

    col = Empty()
    _vs(col).delete_document(1, 1)
    assert col.delete_calls == 0
