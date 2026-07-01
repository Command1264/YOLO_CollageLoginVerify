from __future__ import annotations

from datetime import datetime


class CheckResultProcessor:
    """Transform check results into history, diff text, and notification payloads."""

    def build_payload(self, results: list[dict], semester: str, now: datetime) -> dict:
        """Build UI payload from check result dicts."""
        patch_blocks: list[str] = []
        history_entries: list[dict] = []
        notify_entries: list[dict] = []
        ts = now.strftime("%Y-%m-%d %H:%M:%S")
        semester_text = semester or "目前預設"

        for result in results:
            summary = result.get("summary")
            patch_text = ""
            if isinstance(summary, dict):
                patch_text = str(summary.get("patch_text", ""))
            history_entries.append(
                {
                    "time": ts,
                    "dataset": str(result.get("name", "")),
                    "status": "成功" if bool(result.get("success")) else "失敗",
                    "summary": str(result.get("message", "")),
                    "patch_text": patch_text,
                }
            )
            if not isinstance(summary, dict):
                continue
            patch_blocks.append(f"### {result.get('name', '')}\n{patch_text}")
            added = int(summary.get("added", 0))
            removed = int(summary.get("removed", 0))
            if bool(result.get("success")) and (added > 0 or removed > 0):
                notify_entries.append(
                    {
                        "title": f"[獎助學金更新] {result.get('name', '')}",
                        "summary_text": f"學期：{semester_text}，{result.get('message', '')}",
                        "patch_text": patch_text or "（無）",
                    }
                )

        return {
            "history_entries": history_entries,
            "notifications": notify_entries,
            "diff_text": "\n\n".join(patch_blocks) if len(patch_blocks) != 0 else "（本次沒有可顯示的差異）",
        }
