from dataclasses import dataclass, asdict


@dataclass
class StalenessFlag:
    filename: str
    patch: str
    old_doc: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "StalenessFlag":
        return cls(
            filename=data["filename"],
            patch=data.get("patch", ""),
            old_doc=data.get("old_doc", ""),
        )


@dataclass
class DraftUpdate:
    filename: str
    severity: str
    reasoning: str
    old_doc: str
    new_doc_draft: str
    diff: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "DraftUpdate":
        return cls(
            filename=data["filename"],
            severity=data.get("severity", "REVIEW_RECOMMENDED"),
            reasoning=data.get("reasoning", ""),
            old_doc=data.get("old_doc", ""),
            new_doc_draft=data.get("new_doc_draft", ""),
            diff=data.get("diff", ""),
        )
