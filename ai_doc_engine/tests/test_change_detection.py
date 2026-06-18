from engine.change_detector import ChangeDetector
from engine.staleness_classifier import StalenessClassifier


def classify_patch(patch: str):
    detector = ChangeDetector()
    classifier = StalenessClassifier()
    units = detector.detect(patch)
    flag = classifier.classify("sample.py", units)
    return units, flag


def test_detects_added_function():
    patch = """+def new_func(a, b):
+    return a + b
"""

    units, flag = classify_patch(patch)

    assert len(units) == 1
    assert units[0].name == "new_func"
    assert units[0].change_type == "ADDED_FUNCTION"
    assert flag.severity == "REVIEW_RECOMMENDED"


def test_detects_removed_function():
    patch = """-def old_func(a):
-    return a
"""

    units, flag = classify_patch(patch)

    assert len(units) == 1
    assert units[0].name == "old_func"
    assert units[0].change_type == "REMOVED_FUNCTION"
    assert flag.severity == "BROKEN"


def test_detects_signature_changed():
    patch = """-def calculate(a, b):
+def calculate(a, b, tax):
"""

    units, flag = classify_patch(patch)

    assert len(units) == 1
    assert units[0].name == "calculate"
    assert units[0].change_type == "SIGNATURE_CHANGED"
    assert flag.severity == "BROKEN"


def test_detects_return_type_changed():
    patch = """-def get_name(user_id: int) -> str:
+def get_name(user_id: int) -> dict:
"""

    units, flag = classify_patch(patch)

    assert len(units) == 1
    assert units[0].name == "get_name"
    assert units[0].change_type == "RETURN_TYPE_CHANGED"
    assert units[0].old_return_type == "str"
    assert units[0].new_return_type == "dict"
    assert flag.severity == "POTENTIALLY_OUTDATED"


def test_body_only_change_is_safe():
    patch = """ def add(a, b):
-    return a + b
+    return a + b + 0
"""

    units, flag = classify_patch(patch)

    assert units == []
    assert flag.severity == "SAFE"


def test_removed_takes_priority_over_added():
    patch = """-def old_func(a):
+def new_func(a):
"""

    units, flag = classify_patch(patch)

    assert flag.severity == "BROKEN"


def test_return_type_takes_priority_over_added():
    patch = """-def get_value() -> str:
+def get_value() -> int:
+def helper():
+    pass
"""

    units, flag = classify_patch(patch)

    assert flag.severity == "POTENTIALLY_OUTDATED"


def test_detects_async_function_signature_changed():
    patch = """-async def fetch_data(id: int) -> str:
+async def fetch_data(id: int, include_meta: bool = False) -> str:
"""

    units, flag = classify_patch(patch)

    assert len(units) == 1
    assert units[0].name == "fetch_data"
    assert units[0].change_type == "SIGNATURE_CHANGED"
    assert flag.severity == "BROKEN"


def test_detects_indented_class_method_added():
    patch = """+    def method(self, x):
+        return x
"""

    units, flag = classify_patch(patch)

    assert len(units) == 1
    assert units[0].name == "method"
    assert units[0].change_type == "ADDED_FUNCTION"
    assert flag.severity == "REVIEW_RECOMMENDED"


def test_diff_metadata_lines_are_ignored():
    patch = """--- a/sample.py
+++ b/sample.py
-def old_func(a):
+def old_func(a, b):
"""

    units, flag = classify_patch(patch)

    assert len(units) == 1
    assert units[0].name == "old_func"
    assert units[0].change_type == "SIGNATURE_CHANGED"
    assert flag.severity == "BROKEN"


def test_detects_complex_signature_return_type_changed():
    patch = """-def configure(options=(1, 2), callback=None) -> dict:
+def configure(options=(1, 2), callback=None) -> list:
"""

    units, flag = classify_patch(patch)

    assert len(units) == 1
    assert units[0].name == "configure"
    assert units[0].change_type == "RETURN_TYPE_CHANGED"
    assert units[0].old_return_type == "dict"
    assert units[0].new_return_type == "list"
    assert flag.severity == "POTENTIALLY_OUTDATED"


def test_detects_complex_params_signature_changed():
    patch = """-def run(callback: Callable[[int], str]) -> list[str]:
+def run(callback: Callable[[int], str], retries: int = 3) -> list[str]:
"""

    units, flag = classify_patch(patch)

    assert len(units) == 1
    assert units[0].name == "run"
    assert units[0].change_type == "SIGNATURE_CHANGED"
    assert flag.severity == "BROKEN"
