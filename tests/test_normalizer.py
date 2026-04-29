from src.markdown.normalizer import MarkdownNormalizer


def test_heading_jump_is_fixed() -> None:
    raw = "# Title\n#### Deep\nText\n"
    out = MarkdownNormalizer().normalize(raw)
    assert "## Deep" in out
