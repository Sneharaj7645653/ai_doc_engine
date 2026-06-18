"""Rule-based detection for documentation-impacting function changes."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from engine.models import ChangedUnit


@dataclass
class _FunctionSignature:
    """Parsed function signature data from a single patch line."""

    name: str
    signature: str
    params: str
    return_type: Optional[str]
    line_index: int


class ChangeDetector:
    """Detects function-level changes from a unified Git patch."""

    def detect(self, patch: str) -> list[ChangedUnit]:
        """Return documentation-impacting function changes found in a patch."""

        added: list[_FunctionSignature] = []
        removed: list[_FunctionSignature] = []

        for line_index, line in enumerate(patch.splitlines()):
            if not self._is_diff_content_line(line):
                continue

            parsed = self._parse_function_signature(line, line_index)
            if not parsed:
                continue

            if line.startswith("+"):
                added.append(parsed)
            elif line.startswith("-"):
                removed.append(parsed)

        return self._build_changes(added, removed)

    def _build_changes(
        self,
        added: list[_FunctionSignature],
        removed: list[_FunctionSignature],
    ) -> list[ChangedUnit]:
        changes: list[ChangedUnit] = []
        used_added: set[int] = set()
        used_removed: set[int] = set()

        added_by_name = self._group_by_name(added)
        removed_by_name = self._group_by_name(removed)

        shared_names = set(added_by_name) & set(removed_by_name)

        for name in sorted(shared_names):
            removed_items = removed_by_name[name]
            added_items = added_by_name[name]

            for removed_item in removed_items:
                if removed_item.line_index in used_removed:
                    continue

                exact_match = self._find_same_params_match(
                    removed_item,
                    added_items,
                    used_added,
                )
                if exact_match is None:
                    continue

                used_removed.add(removed_item.line_index)
                used_added.add(exact_match.line_index)

                if self._normalize_return_type(removed_item.return_type) != self._normalize_return_type(
                    exact_match.return_type
                ):
                    changes.append(
                        ChangedUnit(
                            name=name,
                            change_type="RETURN_TYPE_CHANGED",
                            old_signature=removed_item.signature,
                            new_signature=exact_match.signature,
                            old_return_type=removed_item.return_type,
                            new_return_type=exact_match.return_type,
                            reason=f"Return type changed for function '{name}'.",
                        )
                    )

            remaining_removed = [
                item for item in removed_items if item.line_index not in used_removed
            ]
            remaining_added = [
                item for item in added_items if item.line_index not in used_added
            ]

            pair_count = min(len(remaining_removed), len(remaining_added))
            for index in range(pair_count):
                removed_item = remaining_removed[index]
                added_item = remaining_added[index]

                used_removed.add(removed_item.line_index)
                used_added.add(added_item.line_index)

                changes.append(
                    ChangedUnit(
                        name=name,
                        change_type="SIGNATURE_CHANGED",
                        old_signature=removed_item.signature,
                        new_signature=added_item.signature,
                        old_return_type=removed_item.return_type,
                        new_return_type=added_item.return_type,
                        reason=f"Function signature changed for '{name}'.",
                    )
                )

        for removed_item in removed:
            if removed_item.line_index in used_removed:
                continue
            changes.append(
                ChangedUnit(
                    name=removed_item.name,
                    change_type="REMOVED_FUNCTION",
                    old_signature=removed_item.signature,
                    old_return_type=removed_item.return_type,
                    reason=f"Function '{removed_item.name}' was removed.",
                )
            )

        for added_item in added:
            if added_item.line_index in used_added:
                continue
            changes.append(
                ChangedUnit(
                    name=added_item.name,
                    change_type="ADDED_FUNCTION",
                    new_signature=added_item.signature,
                    new_return_type=added_item.return_type,
                    reason=f"Function '{added_item.name}' was added.",
                )
            )

        return changes

    def _find_same_params_match(
        self,
        removed_item: _FunctionSignature,
        added_items: list[_FunctionSignature],
        used_added: set[int],
    ) -> Optional[_FunctionSignature]:
        removed_params = self._normalize_params(removed_item.params)

        for added_item in added_items:
            if added_item.line_index in used_added:
                continue
            if self._normalize_params(added_item.params) == removed_params:
                return added_item

        return None

    def _group_by_name(
        self, items: list[_FunctionSignature]
    ) -> dict[str, list[_FunctionSignature]]:
        grouped: dict[str, list[_FunctionSignature]] = {}
        for item in items:
            grouped.setdefault(item.name, []).append(item)
        return grouped

    def _is_diff_content_line(self, line: str) -> bool:
        return (line.startswith("+") and not line.startswith("+++")) or (
            line.startswith("-") and not line.startswith("---")
        )

    def _parse_function_signature(
        self, line: str, line_index: int
    ) -> Optional[_FunctionSignature]:
        signature = line[1:].strip()
        stripped = line[1:].lstrip()

        if stripped.startswith("async def "):
            header = stripped[len("async def ") :]
        elif stripped.startswith("def "):
            header = stripped[len("def ") :]
        else:
            return None

        match = re.match(r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)", header)
        if not match:
            return None

        remainder = header[match.end() :]
        open_paren_index = self._find_first_non_space(remainder)
        if open_paren_index is None or remainder[open_paren_index] != "(":
            return None

        close_paren_index = self._find_matching_paren(remainder, open_paren_index)
        if close_paren_index is None:
            return None

        params = remainder[open_paren_index + 1 : close_paren_index]
        trailing = remainder[close_paren_index + 1 :].strip()
        return_type = self._extract_return_type(trailing)

        if trailing and self._find_top_level_colon(trailing) is None:
            return None

        return _FunctionSignature(
            name=match.group("name"),
            signature=signature,
            params=params,
            return_type=return_type,
            line_index=line_index,
        )

    def _normalize_params(self, params: str) -> str:
        return re.sub(r"\s+", "", params)

    def _normalize_return_type(self, return_type: Optional[str]) -> Optional[str]:
        if return_type is None:
            return None
        return re.sub(r"\s+", "", return_type)

    def _clean_optional(self, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    def _find_first_non_space(self, value: str) -> Optional[int]:
        for index, char in enumerate(value):
            if not char.isspace():
                return index
        return None

    def _find_matching_paren(self, value: str, open_index: int) -> Optional[int]:
        depth = 0
        string_delimiter: Optional[str] = None
        escaped = False

        for index in range(open_index, len(value)):
            char = value[index]

            if string_delimiter is not None:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == string_delimiter:
                    string_delimiter = None
                continue

            if char in {"'", '"'}:
                string_delimiter = char
                continue

            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    return index

        return None

    def _extract_return_type(self, trailing: str) -> Optional[str]:
        if not trailing:
            return None

        colon_index = self._find_top_level_colon(trailing)
        if colon_index is None:
            return None

        before_colon = trailing[:colon_index].strip()
        if not before_colon.startswith("->"):
            return None

        return self._clean_optional(before_colon[2:])

    def _find_top_level_colon(self, value: str) -> Optional[int]:
        paren_depth = 0
        bracket_depth = 0
        brace_depth = 0
        string_delimiter: Optional[str] = None
        escaped = False

        for index, char in enumerate(value):
            if string_delimiter is not None:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == string_delimiter:
                    string_delimiter = None
                continue

            if char in {"'", '"'}:
                string_delimiter = char
                continue

            if char == "(":
                paren_depth += 1
            elif char == ")":
                paren_depth -= 1
            elif char == "[":
                bracket_depth += 1
            elif char == "]":
                bracket_depth -= 1
            elif char == "{":
                brace_depth += 1
            elif char == "}":
                brace_depth -= 1
            elif (
                char == ":"
                and paren_depth == 0
                and bracket_depth == 0
                and brace_depth == 0
            ):
                return index

        return None
