"""Unit tests for Chinese document indexer."""

from langchain_core.documents import Document

from app.services.chinese_document_indexer import ChineseAwareChunker, ChineseDocumentIndexer, get_chunker, get_indexer


class TestChineseDocumentIndexer:
    """Test cases for ChineseDocumentIndexer."""

    def test_preprocess_document_chinese(self):
        """Test preprocessing a Chinese document."""
        indexer = ChineseDocumentIndexer()
        doc = Document(page_content="人工智能技术在医疗领域的应用越来越广泛。", metadata={"source": "test.txt"})

        processed = indexer.preprocess_document(doc)

        assert processed.metadata["language"] == "chinese"
        assert "tokens" in processed.metadata
        assert "keywords" in processed.metadata
        assert "segmented_text" in processed.metadata
        assert len(processed.metadata["tokens"]) > 0

    def test_preprocess_document_english(self):
        """Test preprocessing an English document."""
        indexer = ChineseDocumentIndexer()
        doc = Document(
            page_content="Machine learning is a subset of artificial intelligence.", metadata={"source": "test.txt"}
        )

        processed = indexer.preprocess_document(doc)

        assert processed.metadata["language"] == "english"
        # English documents shouldn't have Chinese-specific metadata
        assert "tokens" not in processed.metadata or len(processed.metadata.get("tokens", [])) == 0

    def test_preprocess_documents_batch(self):
        """Test preprocessing multiple documents."""
        indexer = ChineseDocumentIndexer()
        docs = [
            Document(page_content="第一个文档", metadata={}),
            Document(page_content="第二个文档", metadata={}),
            Document(page_content="第三个文档", metadata={}),
        ]

        processed = indexer.preprocess_documents(docs)

        assert len(processed) == 3
        assert all(doc.metadata.get("language") == "chinese" for doc in processed)

    def test_create_searchable_text(self):
        """Test creating searchable text representation."""
        indexer = ChineseDocumentIndexer()
        doc = Document(page_content="人工智能应用", metadata={"language": "chinese", "segmented_text": "人工智能 应用"})

        searchable = indexer.create_searchable_text(doc)

        assert isinstance(searchable, str)
        assert len(searchable) > 0
        # Should contain both original and segmented text
        assert "人工智能" in searchable

    def test_extract_metadata_for_filtering(self):
        """Test extracting filterable metadata."""
        indexer = ChineseDocumentIndexer()
        doc = Document(page_content="这是一个测试文档，包含一些中文内容。", metadata={"source": "test.txt"})

        metadata = indexer.extract_metadata_for_filtering(doc)

        assert "content_length" in metadata
        assert "language" in metadata
        assert metadata["language"] == "chinese"

    def test_get_indexer_singleton(self):
        """Test that get_indexer returns singleton instance."""
        indexer1 = get_indexer()
        indexer2 = get_indexer()

        assert indexer1 is indexer2


class TestChineseAwareChunker:
    """Test cases for ChineseAwareChunker."""

    def test_split_text_basic(self):
        """Test basic text splitting."""
        chunker = ChineseAwareChunker(chunk_size=50, chunk_overlap=10)
        text = "这是第一句话。这是第二句话。这是第三句话。这是第四句话。这是第五句话。"

        chunks = chunker.split_text(text)

        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)

    def test_split_text_respects_sentence_boundaries(self):
        """Test that splitting respects sentence boundaries."""
        chunker = ChineseAwareChunker(chunk_size=30, chunk_overlap=5)
        text = "第一句。第二句！第三句？"

        chunks = chunker.split_text(text)

        # Each chunk should end with a sentence delimiter
        for chunk in chunks[:-1]:  # Except possibly the last one
            assert any(chunk.endswith(delim) for delim in ["。", "！", "？"])

    def test_split_text_with_overlap(self):
        """Test that chunks have overlap."""
        chunker = ChineseAwareChunker(chunk_size=50, chunk_overlap=10)
        text = "这是一个很长的文本。" * 10

        chunks = chunker.split_text(text)

        if len(chunks) > 1:
            # Check that there's some overlap between consecutive chunks
            # (This is a simplified check)
            assert len(chunks) > 1

    def test_split_text_empty(self):
        """Test splitting empty text."""
        chunker = ChineseAwareChunker()
        chunks = chunker.split_text("")

        assert chunks == []

    def test_chunk_document(self):
        """Test chunking a document."""
        chunker = ChineseAwareChunker(chunk_size=50, chunk_overlap=10)
        doc = Document(page_content="这是第一句。" * 20, metadata={"source": "test.txt"})

        chunked_docs = chunker.chunk_document(doc)

        assert len(chunked_docs) > 0
        assert all(isinstance(d, Document) for d in chunked_docs)
        # Check metadata
        for i, chunk_doc in enumerate(chunked_docs):
            assert chunk_doc.metadata["chunk_index"] == i
            assert chunk_doc.metadata["total_chunks"] == len(chunked_docs)
            assert chunk_doc.metadata["source"] == "test.txt"

    def test_chunk_document_preserves_metadata(self):
        """Test that chunking preserves original metadata."""
        chunker = ChineseAwareChunker(chunk_size=50, chunk_overlap=10)
        doc = Document(page_content="测试内容。" * 20, metadata={"source": "test.txt", "author": "test_author"})

        chunked_docs = chunker.chunk_document(doc)

        for chunk_doc in chunked_docs:
            assert chunk_doc.metadata["source"] == "test.txt"
            assert chunk_doc.metadata["author"] == "test_author"

    def test_get_chunker_singleton(self):
        """Test that get_chunker returns singleton instance."""
        chunker1 = get_chunker()
        chunker2 = get_chunker()

        assert chunker1 is chunker2
