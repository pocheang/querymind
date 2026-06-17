from pathlib import Path

from app.services.parser_profiles import choose_parser_profile


def test_pdf_uses_pdf_profile():
    profile = choose_parser_profile(Path("report.pdf"), agent_class="pdf_text")

    assert profile["name"] == "pdf_text"
    assert profile["enable_graph"] is True
    assert profile["loader_hint"] == "pdf"


def test_image_uses_ocr_profile():
    profile = choose_parser_profile(Path("scan.png"), agent_class="pdf_text")

    assert profile["name"] == "image_ocr"
    assert profile["loader_hint"] == "image"


def test_policy_filename_uses_policy_profile():
    profile = choose_parser_profile(Path("security-policy.md"), agent_class="policy")

    assert profile["name"] == "policy"
    assert profile["enable_graph"] is True
