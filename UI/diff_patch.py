import difflib
from dataclasses import dataclass


@dataclass
class PatchSummary:
    added: int
    removed: int
    patch_text: str


def build_patch(old_lines: list[str], new_lines: list[str], title: str) -> PatchSummary:
    """Build unified diff text and simple add/remove statistics."""
    diff_lines = list(
        difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"{title}-old",
            tofile=f"{title}-new",
            lineterm="",
        )
    )
    added = 0
    removed = 0
    for line in diff_lines:
        if line.startswith("+++ ") or line.startswith("@@"):
            continue
        if line.startswith("+"):
            added += 1
        elif line.startswith("-") and not line.startswith("--- "):
            removed += 1
    patch_text = "\n".join(diff_lines) if diff_lines else "（無變更）"
    return PatchSummary(added=added, removed=removed, patch_text=patch_text)


def trim_patch_for_message(patch_text: str, limit: int = 1400) -> str:
    """Trim patch text for messaging platforms with length constraints."""
    if len(patch_text) <= limit:
        return patch_text
    head = patch_text[:limit]
    return f"{head}\n...（訊息過長，已截斷）"
