from src.vector.chunker import ChunkerConfig, SemanticChunker


def test_chunker_outputs_multiple_chunks() -> None:
    markdown = "# Intro\n" + ("hello world " * 200)
    chunker = SemanticChunker(ChunkerConfig(chunk_size=120, chunk_overlap=20))
    chunks = chunker.chunk("doc1", markdown)
    assert len(chunks) > 2
    assert chunks[0].doc_id == "doc1"
