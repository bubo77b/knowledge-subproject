from src.metrics.quality import evaluate_markdown_quality


def test_quality_metrics_bounds() -> None:
    md = "# T\n\n|a|b|\n|-|-|\n|1|2|\n\npara"
    txt = "T\na\tb\n1\t2\npara"
    q = evaluate_markdown_quality(md, txt)
    assert 0.0 <= q.structure_integrity <= 1.0
    assert 0.0 <= q.table_fidelity <= 1.0
    assert 0.0 <= q.paragraph_preservation <= 1.0
