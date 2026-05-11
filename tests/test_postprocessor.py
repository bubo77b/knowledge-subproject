"""Tests for omniparser.postprocessor."""

from omniparser.postprocessor import MarkdownPostProcessor


class TestMarkdownPostProcessor:
    def setup_method(self):
        self.proc = MarkdownPostProcessor()

    def test_heading_level_fix(self):
        md = "# Title\n#### Skipped to h4\nContent"
        result = self.proc.process(md)
        assert "## Skipped to h4" in result
        assert "####" not in result

    def test_consecutive_headings_normalized(self):
        md = "# H1\n### Jumped to h3\n##### Jumped to h5"
        result = self.proc.process(md)
        lines = [ln for ln in result.splitlines() if ln.startswith("#")]
        assert lines[0].startswith("# ")
        assert lines[1].startswith("## ")
        assert lines[2].startswith("### ")

    def test_broken_line_rejoining(self):
        md = "This is a broken\nline that should be joined"
        result = self.proc.process(md)
        assert "broken line" in result

    def test_line_not_joined_after_punctuation(self):
        md = "End of sentence.\nNew sentence starts here."
        result = self.proc.process(md)
        assert "sentence.\n" in result

    def test_heading_not_joined(self):
        md = "Some text\n# Heading"
        result = self.proc.process(md)
        assert "\n# Heading" in result

    def test_latex_normalisation_inline(self):
        md = r"The formula \(E=mc^2\) is famous."
        result = self.proc.process(md)
        assert "$E=mc^2$" in result

    def test_latex_normalisation_display(self):
        md = r"The equation: \[a^2 + b^2 = c^2\]"
        result = self.proc.process(md)
        assert "$$a^2 + b^2 = c^2$$" in result

    def test_collapse_blank_lines(self):
        md = "Para 1\n\n\n\n\nPara 2"
        result = self.proc.process(md)
        assert "\n\n\n" not in result
        assert "Para 1\n\nPara 2" in result

    def test_table_pipe_trimming(self):
        md = "|  col1  |  col2  |\n|---|---|\n|  a  |  b  |"
        result = self.proc.process(md)
        for line in result.strip().splitlines():
            if "|" in line:
                assert "  |" not in line or "|  " not in line

    def test_output_ends_with_newline(self):
        md = "hello"
        result = self.proc.process(md)
        assert result.endswith("\n")
