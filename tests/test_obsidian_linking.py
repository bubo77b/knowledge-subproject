from src.obsidian.linker import ObsidianLinker


def test_keyword_extract_and_link() -> None:
    linker = ObsidianLinker(synonym_map={"llm": "large_language_model"}, keyword_top_k=5)
    md = "LLM helps build retrieval system for personal assistant."
    kws = linker.extract_keywords(md)
    linked, used = linker.inject_wikilinks(md, kws)
    assert kws
    assert used
    assert "[[" in linked
