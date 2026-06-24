import sys
import os
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine.models import StalenessFlag, DraftUpdate
from engine.update_drafter import UpdateDrafter
from engine.llm_service import LLMService


# ── Fixtures ──────────────────────────────────────────────────────────────────

SAMPLE_PATCH = "@@ -1,3 +1,4 @@\n def foo():\n-    return 1\n+    return 2\n+    # new line"
OLD_DOC = "# foo\n\nReturns 1 always."
NEW_DOC = "# foo\n\nReturns 2 always."


def make_drafter(llm_response: dict) -> UpdateDrafter:
    mock_llm = MagicMock(spec=LLMService)
    mock_llm.detect_staleness_and_draft.return_value = llm_response
    return UpdateDrafter(mock_llm)


# ── StalenessFlag ─────────────────────────────────────────────────────────────

class TestStalenessFlag:
    def test_to_dict_roundtrip(self):
        flag = StalenessFlag(filename="foo.py", patch=SAMPLE_PATCH, old_doc=OLD_DOC)
        assert StalenessFlag.from_dict(flag.to_dict()) == flag

    def test_from_dict_missing_patch_defaults_empty(self):
        flag = StalenessFlag.from_dict({"filename": "x.py", "old_doc": OLD_DOC})
        assert flag.patch == ""

    def test_from_dict_missing_old_doc_defaults_empty(self):
        flag = StalenessFlag.from_dict({"filename": "x.py", "patch": SAMPLE_PATCH})
        assert flag.old_doc == ""


# ── DraftUpdate ───────────────────────────────────────────────────────────────

class TestDraftUpdate:
    def test_to_dict_roundtrip(self):
        draft = DraftUpdate(
            filename="bar.py",
            severity="BROKEN",
            reasoning="Signature changed.",
            old_doc=OLD_DOC,
            new_doc_draft=NEW_DOC,
            diff="--- a\n+++ b\n",
        )
        assert DraftUpdate.from_dict(draft.to_dict()) == draft

    def test_from_dict_defaults(self):
        draft = DraftUpdate.from_dict({"filename": "x.py"})
        assert draft.severity == "REVIEW_RECOMMENDED"
        assert draft.reasoning == ""
        assert draft.diff == ""


# ── UpdateDrafter ─────────────────────────────────────────────────────────────

class TestUpdateDrafter:
    def test_draft_returns_draft_update_instance(self):
        drafter = make_drafter({"severity": "BROKEN", "reasoning": "sig changed", "updated_doc": NEW_DOC})
        flag = StalenessFlag(filename="foo.py", patch=SAMPLE_PATCH, old_doc=OLD_DOC)
        result = drafter.draft(flag)
        assert isinstance(result, DraftUpdate)

    def test_draft_propagates_severity(self):
        drafter = make_drafter({"severity": "BROKEN", "reasoning": "x", "updated_doc": NEW_DOC})
        flag = StalenessFlag(filename="foo.py", patch=SAMPLE_PATCH, old_doc=OLD_DOC)
        assert drafter.draft(flag).severity == "BROKEN"

    def test_draft_propagates_reasoning(self):
        drafter = make_drafter({"severity": "BROKEN", "reasoning": "sig changed", "updated_doc": NEW_DOC})
        flag = StalenessFlag(filename="foo.py", patch=SAMPLE_PATCH, old_doc=OLD_DOC)
        assert drafter.draft(flag).reasoning == "sig changed"

    def test_draft_propagates_new_doc(self):
        drafter = make_drafter({"severity": "BROKEN", "reasoning": "x", "updated_doc": NEW_DOC})
        flag = StalenessFlag(filename="foo.py", patch=SAMPLE_PATCH, old_doc=OLD_DOC)
        assert drafter.draft(flag).new_doc_draft == NEW_DOC

    def test_draft_computes_non_empty_diff_when_docs_differ(self):
        drafter = make_drafter({"severity": "BROKEN", "reasoning": "x", "updated_doc": NEW_DOC})
        flag = StalenessFlag(filename="foo.py", patch=SAMPLE_PATCH, old_doc=OLD_DOC)
        diff = drafter.draft(flag).diff
        assert diff != ""
        assert "---" in diff
        assert "+++" in diff

    def test_draft_empty_diff_when_docs_identical(self):
        drafter = make_drafter({"severity": "SAFE", "reasoning": "no change", "updated_doc": OLD_DOC})
        flag = StalenessFlag(filename="foo.py", patch=SAMPLE_PATCH, old_doc=OLD_DOC)
        assert drafter.draft(flag).diff == ""

    def test_draft_falls_back_to_old_doc_when_updated_doc_missing(self):
        drafter = make_drafter({"severity": "REVIEW_RECOMMENDED", "reasoning": "maybe"})
        flag = StalenessFlag(filename="foo.py", patch=SAMPLE_PATCH, old_doc=OLD_DOC)
        assert drafter.draft(flag).new_doc_draft == OLD_DOC

    def test_draft_preserves_filename(self):
        drafter = make_drafter({"severity": "BROKEN", "reasoning": "x", "updated_doc": NEW_DOC})
        flag = StalenessFlag(filename="src/utils.py", patch=SAMPLE_PATCH, old_doc=OLD_DOC)
        assert drafter.draft(flag).filename == "src/utils.py"

    def test_diff_includes_filename_in_headers(self):
        drafter = make_drafter({"severity": "BROKEN", "reasoning": "x", "updated_doc": NEW_DOC})
        flag = StalenessFlag(filename="foo.py", patch=SAMPLE_PATCH, old_doc=OLD_DOC)
        diff = drafter.draft(flag).diff
        assert "foo.py" in diff


# ── LLMService JSON parsing ───────────────────────────────────────────────────

class TestLLMServiceJsonParsing:
    def _make_service(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": "test"}):
            with patch("engine.llm_service.Groq"):
                return LLMService()

    def test_parse_valid_json(self):
        svc = self._make_service()
        raw = '{"severity": "BROKEN", "reasoning": "sig changed", "updated_doc": "# New"}'
        result = svc._parse_json_response(raw, OLD_DOC)
        assert result["severity"] == "BROKEN"
        assert result["reasoning"] == "sig changed"
        assert result["updated_doc"] == "# New"

    def test_parse_json_in_code_fence(self):
        svc = self._make_service()
        raw = '```json\n{"severity": "SAFE", "reasoning": "ok", "updated_doc": "x"}\n```'
        result = svc._parse_json_response(raw, OLD_DOC)
        assert result["severity"] == "SAFE"

    def test_parse_invalid_severity_normalised(self):
        svc = self._make_service()
        raw = '{"severity": "UNKNOWN_VALUE", "reasoning": "x", "updated_doc": "y"}'
        result = svc._parse_json_response(raw, OLD_DOC)
        assert result["severity"] == "REVIEW_RECOMMENDED"

    def test_parse_non_json_returns_fallback(self):
        svc = self._make_service()
        result = svc._parse_json_response("This is not JSON at all.", OLD_DOC)
        assert result["severity"] == "REVIEW_RECOMMENDED"
        assert result["updated_doc"] == OLD_DOC
        assert "manual review" in result["reasoning"].lower()

    def test_severity_uppercased(self):
        svc = self._make_service()
        raw = '{"severity": "broken", "reasoning": "x", "updated_doc": "y"}'
        result = svc._parse_json_response(raw, OLD_DOC)
        assert result["severity"] == "BROKEN"
