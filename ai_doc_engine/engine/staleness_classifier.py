"""Classify documentation staleness severity from detected code changes."""

from engine.models import ChangedUnit, StalenessFlag


class StalenessClassifier:
    """Maps detected function changes to a documentation staleness severity."""

    def classify(
        self, filename: str, changed_units: list[ChangedUnit]
    ) -> StalenessFlag:
        """Return the final staleness flag for a file."""

        if not changed_units:
            return StalenessFlag(
                filename=filename,
                severity="SAFE",
                reason="No public function or signature-level documentation impact detected.",
                changed_units=changed_units,
            )

        removed = self._find_first_by_type(changed_units, "REMOVED_FUNCTION")
        if removed is not None:
            return StalenessFlag(
                filename=filename,
                severity="BROKEN",
                reason=f"Documentation is likely broken because function '{removed.name}' was removed.",
                changed_units=changed_units,
            )

        signature_changed = self._find_first_by_type(
            changed_units, "SIGNATURE_CHANGED"
        )
        if signature_changed is not None:
            return StalenessFlag(
                filename=filename,
                severity="BROKEN",
                reason=(
                    f"Documentation is likely broken because function "
                    f"'{signature_changed.name}' changed its signature."
                ),
                changed_units=changed_units,
            )

        return_type_changed = self._find_first_by_type(
            changed_units, "RETURN_TYPE_CHANGED"
        )
        if return_type_changed is not None:
            return StalenessFlag(
                filename=filename,
                severity="POTENTIALLY_OUTDATED",
                reason=(
                    f"Documentation may be outdated because function "
                    f"'{return_type_changed.name}' changed its return type."
                ),
                changed_units=changed_units,
            )

        if self._all_added_functions(changed_units):
            return StalenessFlag(
                filename=filename,
                severity="REVIEW_RECOMMENDED",
                reason="New function documentation may be needed for recently added functions.",
                changed_units=changed_units,
            )

        return StalenessFlag(
            filename=filename,
            severity="SAFE",
            reason="No public function or signature-level documentation impact detected.",
            changed_units=changed_units,
        )

    def _find_first_by_type(
        self, changed_units: list[ChangedUnit], change_type: str
    ) -> ChangedUnit | None:
        for unit in changed_units:
            if unit.change_type == change_type:
                return unit
        return None

    def _all_added_functions(self, changed_units: list[ChangedUnit]) -> bool:
        return all(unit.change_type == "ADDED_FUNCTION" for unit in changed_units)
