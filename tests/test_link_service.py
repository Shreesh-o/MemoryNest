"""Tests for the Document Map link service."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.database.repositories import (
    ChunkRepository,
    DocumentLinkRepository,
    DocumentRepository,
    UserRepository,
)
from app.services.link_service import (
    _compute_tfidf,
    _get_shared_terms,
    _tokenize,
    compute_links,
    get_document_vectors,
    rebuild_links,
)
from app.utils.config import LINK_MIN_SIMILARITY, LINK_STORE_MIN_SIMILARITY


class TestTokenize:
    def test_basic_tokenization(self):
        tokens = _tokenize("Hello world! This is a test document.")
        assert "hello" in tokens
        assert "world" in tokens
        assert "test" in tokens
        assert "document" in tokens

    def test_drops_short_tokens(self):
        tokens = _tokenize("a an is it the")
        assert tokens == []

    def test_drops_stopwords(self):
        tokens = _tokenize("the and or but for with")
        assert tokens == []

    def test_drops_numbers(self):
        tokens = _tokenize("version 123 4567 test")
        assert "test" in tokens
        assert "123" not in tokens
        assert "4567" not in tokens

    def test_lowercase(self):
        tokens = _tokenize("HELLO World")
        assert "hello" in tokens
        assert "world" in tokens

    def test_splits_on_non_letters(self):
        tokens = _tokenize("hello-world,test.document")
        assert "hello" in tokens
        assert "world" in tokens
        assert "test" in tokens
        assert "document" in tokens


class TestTFIDF:
    def test_compute_tfidf_basic(self):
        docs = [
            (1, "machine learning algorithms"),
            (2, "deep learning neural networks"),
            (3, "natural language processing"),
        ]
        doc_tf, idf = _compute_tfidf(docs)

        assert 1 in doc_tf
        assert 2 in doc_tf
        assert 3 in doc_tf

        # "learning" appears in 2 docs, so IDF = log(3/2)
        assert "learning" in idf
        assert idf["learning"] > 0

        # "machine" appears in 1 doc, IDF = log(3/1)
        assert "machine" in idf
        assert idf["machine"] > idf["learning"]

    def test_tfidf_term_frequencies(self):
        docs = [
            (1, "test test test document"),
            (2, "test document"),
        ]
        doc_tf, idf = _compute_tfidf(docs)

        assert doc_tf[1]["test"] == 3
        assert doc_tf[2]["test"] == 1


class TestSharedTerms:
    def test_shared_terms_basic(self):
        docs = [
            (1, "machine learning algorithms"),
            (2, "deep learning neural networks"),
        ]
        doc_tf, idf = _compute_tfidf(docs)

        shared = _get_shared_terms(1, 2, doc_tf, idf)
        assert "learning" in shared

    def test_shared_terms_max_limit(self):
        docs = [
            (1, "alpha beta gamma delta epsilon zeta"),
            (2, "alpha beta gamma delta epsilon zeta"),
        ]
        doc_tf, idf = _compute_tfidf(docs)

        shared = _get_shared_terms(1, 2, doc_tf, idf, max_terms=3)
        assert len(shared) <= 3

    def test_no_shared_terms(self):
        docs = [
            (1, "machine learning"),
            (2, "cooking recipes"),
        ]
        doc_tf, idf = _compute_tfidf(docs)

        shared = _get_shared_terms(1, 2, doc_tf, idf)
        assert shared == []


class TestGetDocumentVectors:
    def test_empty_user(self, tmp_path, monkeypatch):
        """User with no documents returns empty dict."""
        vectors = get_document_vectors(999)
        assert vectors == {}

    def test_skips_documents_without_chunks(self, tmp_path, monkeypatch):
        """Documents with no chunk embeddings are skipped."""
        from app.services import vector_service
        vs = vector_service.get_vector_service()

        # Create a user and document
        user_repo = UserRepository()
        user = user_repo.create("testuser", "hash")

        doc_repo = DocumentRepository()
        doc = doc_repo.create(user.id, "empty.txt", "/tmp/empty.txt", "txt")
        doc_repo.set_text(doc.id, user.id, "preview", 0)  # No chunks

        vectors = get_document_vectors(user.id)
        assert vectors == {}


class TestComputeLinks:
    def test_zero_documents_returns_empty(self, monkeypatch):
        """User with 0 documents returns no links."""
        monkeypatch.setattr("app.services.link_service.get_document_vectors", lambda uid: {})
        links = compute_links(1)
        assert links == []

    def test_one_document_returns_empty(self, monkeypatch):
        """User with 1 document returns no links."""
        vec = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        monkeypatch.setattr("app.services.link_service.get_document_vectors", lambda uid: {1: vec})
        links = compute_links(1)
        assert links == []

    def test_threshold_respected(self, monkeypatch):
        """Pairs below min_score are not included."""
        vec1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        vec2 = np.array([0.0, 1.0, 0.0], dtype=np.float32)  # orthogonal = 0 similarity
        monkeypatch.setattr(
            "app.services.link_service.get_document_vectors",
            lambda uid: {1: vec1, 2: vec2},
        )
        with patch("app.services.link_service.ChunkRepository") as mock_chunk_repo:
            mock_chunk = MagicMock()
            mock_chunk.content = "machine learning"
            mock_chunk_repo.return_value.list_for_document.return_value = [mock_chunk]

            links = compute_links(1, min_score=0.5)
            assert links == []

    def test_top_n_behavior(self, monkeypatch):
        """Only top max_per_doc neighbors are kept per document.

        Algorithm: keep pair if score >= min_score AND pair is in top-N of AT LEAST ONE doc.
        Doc 1 is closest to all others. So docs 2,3,4,5 each have doc 1 as top-1.
        Thus all 4 pairs (1,2), (1,3), (1,4), (1,5) are kept.
        """
        vec1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        vec2 = np.array([0.9, 0.1, 0.0], dtype=np.float32)
        vec3 = np.array([0.8, 0.2, 0.0], dtype=np.float32)
        vec4 = np.array([0.7, 0.3, 0.0], dtype=np.float32)
        vec5 = np.array([0.6, 0.4, 0.0], dtype=np.float32)

        monkeypatch.setattr(
            "app.services.link_service.get_document_vectors",
            lambda uid: {1: vec1, 2: vec2, 3: vec3, 4: vec4, 5: vec5},
        )

        with patch("app.services.link_service.ChunkRepository") as mock_chunk_repo:
            mock_chunk = MagicMock()
            mock_chunk.content = "test content"
            mock_chunk_repo.return_value.list_for_document.return_value = [mock_chunk]

            links = compute_links(1, min_score=0.5, max_per_doc=2)
            # Doc 1 is in top-2 for docs 2,3,4,5 (since it's their #1 neighbor)
            # So all 4 pairs involving doc 1 are kept
            doc1_links = [l for l in links if l["doc_a"] == 1 or l["doc_b"] == 1]
            assert len(doc1_links) == 4

    def test_pair_stored_once(self, monkeypatch):
        """Each document pair appears only once with doc_a < doc_b."""
        vec1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        vec2 = np.array([0.9, 0.1, 0.0], dtype=np.float32)
        monkeypatch.setattr(
            "app.services.link_service.get_document_vectors",
            lambda uid: {1: vec1, 2: vec2},
        )

        with patch("app.services.link_service.ChunkRepository") as mock_chunk_repo:
            mock_chunk = MagicMock()
            mock_chunk.content = "test content"
            mock_chunk_repo.return_value.list_for_document.return_value = [mock_chunk]

            links = compute_links(1, min_score=0.5)
            assert len(links) == 1
            assert links[0]["doc_a"] == 1
            assert links[0]["doc_b"] == 2

    def test_shared_terms_sensible(self, monkeypatch):
        """Shared terms are actually shared and ranked by TF-IDF."""
        vec1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        vec2 = np.array([0.9, 0.1, 0.0], dtype=np.float32)
        monkeypatch.setattr(
            "app.services.link_service.get_document_vectors",
            lambda uid: {1: vec1, 2: vec2},
        )

        with patch("app.services.link_service.ChunkRepository") as mock_chunk_repo:
            chunk1 = MagicMock()
            chunk1.content = "machine learning algorithms deep learning"
            chunk2 = MagicMock()
            chunk2.content = "deep learning neural networks machine learning"

            def list_for_doc(doc_id, user_id):
                if doc_id == 1:
                    return [chunk1]
                return [chunk2]

            mock_chunk_repo.return_value.list_for_document.side_effect = list_for_doc

            links = compute_links(1, min_score=0.5)
            assert len(links) == 1
            shared = json.loads(links[0]["shared_terms"])
            assert "learning" in shared
            assert "machine" in shared or "deep" in shared

    def test_user_isolation(self, monkeypatch):
        """Links are computed per user, no cross-user leakage."""
        vec1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        vec2 = np.array([0.9, 0.1, 0.0], dtype=np.float32)

        def mock_get_vectors(uid):
            if uid == 1:
                return {1: vec1, 2: vec2}
            return {}

        monkeypatch.setattr("app.services.link_service.get_document_vectors", mock_get_vectors)

        with patch("app.services.link_service.ChunkRepository") as mock_chunk_repo:
            mock_chunk = MagicMock()
            mock_chunk.content = "test content"
            mock_chunk_repo.return_value.list_for_document.return_value = [mock_chunk]

            links_user1 = compute_links(1, min_score=0.5)
            links_user2 = compute_links(2, min_score=0.5)

            assert len(links_user1) == 1
            assert len(links_user2) == 0

    def test_store_threshold_vs_read_threshold(self, monkeypatch):
        """Links between LINK_STORE_MIN_SIMILARITY (0.30) and LINK_MIN_SIMILARITY (0.45)
        are stored but hidden at the default read threshold.
        """
        # Create vectors with similarity ~0.35 (between store and read threshold)
        vec1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        # 0.35 similarity = dot product of normalized vectors
        vec2 = np.array([0.35, np.sqrt(1 - 0.35**2), 0.0], dtype=np.float32)

        monkeypatch.setattr(
            "app.services.link_service.get_document_vectors",
            lambda uid: {1: vec1, 2: vec2},
        )

        with patch("app.services.link_service.ChunkRepository") as mock_chunk_repo:
            mock_chunk = MagicMock()
            mock_chunk.content = "test content"
            mock_chunk_repo.return_value.list_for_document.return_value = [mock_chunk]

            # Using store threshold (0.30) should include the link
            links_store = compute_links(1, use_store_threshold=True)
            assert len(links_store) == 1
            assert links_store[0]["score"] >= LINK_STORE_MIN_SIMILARITY

            # Using read threshold (0.45) should NOT include the link
            links_read = compute_links(1, use_store_threshold=False)
            assert len(links_read) == 0

            # Explicit min_score=0.30 should include
            links_explicit_low = compute_links(1, min_score=0.30)
            assert len(links_explicit_low) == 1

            # Explicit min_score=0.45 should NOT include
            links_explicit_high = compute_links(1, min_score=0.45)
            assert len(links_explicit_high) == 0


class TestRebuildLinks:
    def test_rebuild_persists_links(self, tmp_path, monkeypatch):
        """rebuild_links stores links in the database."""
        user_repo = UserRepository()
        user = user_repo.create("testuser", "hash")

        # Create documents first
        doc_repo = DocumentRepository()
        doc1 = doc_repo.create(user.id, "doc1.txt", "/tmp/doc1.txt", "txt")
        doc_repo.set_text(doc1.id, user.id, "preview", 1)
        doc2 = doc_repo.create(user.id, "doc2.txt", "/tmp/doc2.txt", "txt")
        doc_repo.set_text(doc2.id, user.id, "preview", 1)

        vec1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        vec2 = np.array([0.9, 0.1, 0.0], dtype=np.float32)
        monkeypatch.setattr(
            "app.services.link_service.get_document_vectors",
            lambda uid: {doc1.id: vec1, doc2.id: vec2} if uid == user.id else {},
        )

        with patch("app.services.link_service.ChunkRepository") as mock_chunk_repo:
            chunk1 = MagicMock()
            chunk1.content = "machine learning"
            chunk2 = MagicMock()
            chunk2.content = "deep learning"
            mock_chunk_repo.return_value.list_for_document.side_effect = lambda doc_id, user_id: (
                [chunk1] if doc_id == doc1.id else [chunk2]
            )

            links = rebuild_links(user.id)
            assert len(links) == 1

            link_repo = DocumentLinkRepository()
            stored = link_repo.list_links(user.id)
            assert len(stored) == 1
            assert stored[0].doc_a == doc1.id
            assert stored[0].doc_b == doc2.id

    def test_rebuild_replaces_existing(self, tmp_path, monkeypatch):
        """rebuild_links replaces existing links for the user."""
        user_repo = UserRepository()
        user = user_repo.create("testuser", "hash")

        # Create documents for first rebuild
        doc_repo = DocumentRepository()
        doc1 = doc_repo.create(user.id, "doc1.txt", "/tmp/doc1.txt", "txt")
        doc_repo.set_text(doc1.id, user.id, "preview", 1)
        doc2 = doc_repo.create(user.id, "doc2.txt", "/tmp/doc2.txt", "txt")
        doc_repo.set_text(doc2.id, user.id, "preview", 1)

        vec1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        vec2 = np.array([0.9, 0.1, 0.0], dtype=np.float32)
        monkeypatch.setattr(
            "app.services.link_service.get_document_vectors",
            lambda uid: {doc1.id: vec1, doc2.id: vec2} if uid == user.id else {},
        )

        with patch("app.services.link_service.ChunkRepository") as mock_chunk_repo:
            chunk1 = MagicMock()
            chunk1.content = "machine learning"
            chunk2 = MagicMock()
            chunk2.content = "deep learning"
            mock_chunk_repo.return_value.list_for_document.side_effect = lambda doc_id, user_id: (
                [chunk1] if doc_id == doc1.id else [chunk2]
            )

            rebuild_links(user.id)

        # Create new documents for second rebuild
        doc3 = doc_repo.create(user.id, "doc3.txt", "/tmp/doc3.txt", "txt")
        doc_repo.set_text(doc3.id, user.id, "preview", 1)
        doc4 = doc_repo.create(user.id, "doc4.txt", "/tmp/doc4.txt", "txt")
        doc_repo.set_text(doc4.id, user.id, "preview", 1)

        # Second rebuild with different docs
        vec3 = np.array([0.0, 0.0, 1.0], dtype=np.float32)
        vec4 = np.array([0.1, 0.0, 0.9], dtype=np.float32)
        monkeypatch.setattr(
            "app.services.link_service.get_document_vectors",
            lambda uid: {doc3.id: vec3, doc4.id: vec4} if uid == user.id else {},
        )

        with patch("app.services.link_service.ChunkRepository") as mock_chunk_repo:
            chunk3 = MagicMock()
            chunk3.content = "neural networks"
            chunk4 = MagicMock()
            chunk4.content = "deep networks"
            mock_chunk_repo.return_value.list_for_document.side_effect = lambda doc_id, user_id: (
                [chunk3] if doc_id == doc3.id else [chunk4]
            )

            rebuild_links(user.id)

        # Should only have the new links
        link_repo = DocumentLinkRepository()
        stored = link_repo.list_links(user.id)
        assert len(stored) == 1
        assert stored[0].doc_a == doc3.id
        assert stored[0].doc_b == doc4.id


class TestDocumentLinkRepository:
    def test_list_links_for_document(self, tmp_path):
        """list_links_for_document returns links involving the document."""
        user_repo = UserRepository()
        user = user_repo.create("testuser", "hash")

        # Create documents
        doc_repo = DocumentRepository()
        doc1 = doc_repo.create(user.id, "doc1.txt", "/tmp/doc1.txt", "txt")
        doc2 = doc_repo.create(user.id, "doc2.txt", "/tmp/doc2.txt", "txt")
        doc3 = doc_repo.create(user.id, "doc3.txt", "/tmp/doc3.txt", "txt")
        doc4 = doc_repo.create(user.id, "doc4.txt", "/tmp/doc4.txt", "txt")

        link_repo = DocumentLinkRepository()
        # Manually insert some links using real doc IDs
        link_repo.replace_links_for_user(user.id, [
            {"doc_a": doc1.id, "doc_b": doc2.id, "score": 0.9, "shared_terms": '["learning"]'},
            {"doc_a": doc2.id, "doc_b": doc3.id, "score": 0.8, "shared_terms": '["deep"]'},
            {"doc_a": doc1.id, "doc_b": doc4.id, "score": 0.7, "shared_terms": '["algo"]'},
        ])

        # Links for doc 2 should return both (1,2) and (2,3)
        links_for_2 = link_repo.list_links_for_document(user.id, doc2.id)
        assert len(links_for_2) == 2

        # Links for doc 1 should return (1,2) and (1,4)
        links_for_1 = link_repo.list_links_for_document(user.id, doc1.id)
        assert len(links_for_1) == 2

    def test_cascade_delete_user(self, tmp_path):
        """When user is deleted, their links are cascade deleted."""
        user_repo = UserRepository()
        user = user_repo.create("testuser", "hash")

        doc_repo = DocumentRepository()
        doc1 = doc_repo.create(user.id, "doc1.txt", "/tmp/doc1.txt", "txt")
        doc2 = doc_repo.create(user.id, "doc2.txt", "/tmp/doc2.txt", "txt")

        link_repo = DocumentLinkRepository()
        link_repo.replace_links_for_user(user.id, [
            {"doc_a": doc1.id, "doc_b": doc2.id, "score": 0.9, "shared_terms": '["learning"]'},
        ])

        # Delete user
        user_repo.delete(user.id)

        # Links should be gone
        links = link_repo.list_links(user.id)
        assert len(links) == 0

    def test_cascade_delete_document(self, tmp_path):
        """When document is deleted, links involving it are cascade deleted."""
        user_repo = UserRepository()
        user = user_repo.create("testuser", "hash")

        doc_repo = DocumentRepository()
        doc1 = doc_repo.create(user.id, "doc1.txt", "/tmp/doc1.txt", "txt")
        doc_repo.set_text(doc1.id, user.id, "preview", 1)
        doc2 = doc_repo.create(user.id, "doc2.txt", "/tmp/doc2.txt", "txt")
        doc_repo.set_text(doc2.id, user.id, "preview", 1)
        doc3 = doc_repo.create(user.id, "doc3.txt", "/tmp/doc3.txt", "txt")
        doc_repo.set_text(doc3.id, user.id, "preview", 1)

        link_repo = DocumentLinkRepository()
        link_repo.replace_links_for_user(user.id, [
            {"doc_a": doc1.id, "doc_b": doc2.id, "score": 0.9, "shared_terms": '["learning"]'},
            {"doc_a": doc2.id, "doc_b": doc3.id, "score": 0.8, "shared_terms": '["deep"]'},
        ])

        # Delete doc2
        doc_repo.delete(doc2.id, user.id)

        # Links involving doc2 should be gone
        links = link_repo.list_links(user.id)
        assert len(links) == 0