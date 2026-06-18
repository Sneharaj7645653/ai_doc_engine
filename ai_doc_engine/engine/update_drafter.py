import difflib
from .models import StalenessFlag, DraftUpdate
from .llm_service import LLMService


class UpdateDrafter:
    def __init__(self, llm_service: LLMService):
        self.llm = llm_service

    def draft(self, flag: StalenessFlag) -> DraftUpdate:
        result = self.llm.detect_staleness_and_draft(flag.old_doc, flag.patch)

        severity = result.get("severity", "REVIEW_RECOMMENDED")
        reasoning = result.get("reasoning", "")
        new_doc = result.get("updated_doc", flag.old_doc)

        diff = self._compute_diff(flag.old_doc, new_doc, flag.filename)

        return DraftUpdate(
            filename=flag.filename,
            severity=severity,
            reasoning=reasoning,
            old_doc=flag.old_doc,
            new_doc_draft=new_doc,
            diff=diff,
        )

    @staticmethod
    def _compute_diff(old: str, new: str, filename: str) -> str:
        old_lines = old.splitlines(keepends=True)
        new_lines = new.splitlines(keepends=True)
        diff_lines = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
        )
        return "".join(diff_lines)
