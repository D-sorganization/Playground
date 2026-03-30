"""Auto-generated syntax verification tests for video_ingest."""

import src.Project_GROOT.tools.video_ingest as target_module


def test_module_syntax_and_import():
    """Verify Project_GROOT.tools.video_ingest can be imported."""
    assert target_module is not None


def test_has_symbol_VideoIngester():
    """Verify VideoIngester exists in module."""
    assert hasattr(target_module, "VideoIngester")


def test_has_symbol_main():
    """Verify main exists in module."""
    assert hasattr(target_module, "main")
