from __future__ import annotations

import threading
import uuid
from datetime import datetime


class CheckQueueCoordinator:
    """Coordinate external IPC check jobs and queue status transitions."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._ipc_jobs: dict[str, dict] = {}
        self._ipc_inbox: list[dict[str, str]] = []

    def enqueue_external_job(
        self,
        semester: str,
        requester: str,
        service_boot_ready: bool,
        check_running: bool,
        pending_count: int,
    ) -> dict:
        """Register external check request and return initial job payload."""
        job_id = str(uuid.uuid4())
        semester_value = semester.strip()
        request_time = self._now_text()
        with self._lock:
            if not service_boot_ready:
                payload = {
                    "job_id": job_id,
                    "status": "loading",
                    "progress": 0,
                    "message": "ScholarshipService 啟動中",
                    "queue_ahead": 0,
                    "semester": semester_value,
                    "requester": requester,
                    "created_at": request_time,
                    "updated_at": request_time,
                }
                self._ipc_jobs[job_id] = payload
                return {"success": True, **payload}

            queue_ahead = (1 if check_running else 0) + pending_count + len(self._ipc_inbox)
            payload = {
                "job_id": job_id,
                "status": "queued",
                "progress": 0,
                "message": "已加入檢查佇列",
                "queue_ahead": queue_ahead,
                "semester": semester_value,
                "requester": requester,
                "created_at": request_time,
                "updated_at": request_time,
            }
            self._ipc_jobs[job_id] = payload
            self._ipc_inbox.append({
                "type": "external",
                "job_id": job_id,
                "semester": semester_value,
                "requester": requester,
            })
            return {"success": True, **payload}

    def get_job_status(self, job_id: str) -> dict:
        """Return one external job status payload."""
        with self._lock:
            payload = self._ipc_jobs.get(job_id)
            if payload is None:
                return {"success": False, "status": "not_found", "error": "job_not_found"}
            return {"success": True, **payload}

    def drain_ipc_inbox(self) -> list[dict[str, str]]:
        """Drain and return pending external queue entries."""
        with self._lock:
            if len(self._ipc_inbox) == 0:
                return []
            incoming = list(self._ipc_inbox)
            self._ipc_inbox.clear()
            return incoming

    def update_queue_ahead(self, pending_check_queue: list[dict[str, str]], check_running: bool) -> None:
        """Update queue ahead values for queued external jobs."""
        queued_map: dict[str, int] = {}
        running_offset = 1 if check_running else 0
        for idx, entry in enumerate(pending_check_queue):
            if entry.get("type") != "external":
                continue
            job_id = str(entry.get("job_id", "")).strip()
            if job_id == "":
                continue
            queued_map[job_id] = running_offset + idx

        now_text = self._now_text()
        with self._lock:
            for job_id, queue_ahead in queued_map.items():
                payload = self._ipc_jobs.get(job_id)
                if payload is None:
                    continue
                if payload.get("status") != "queued":
                    continue
                payload["queue_ahead"] = queue_ahead
                payload["updated_at"] = now_text

    def mark_context_running(self, context: dict[str, str] | None) -> None:
        """Mark running for an external current context."""
        job_id = self._extract_external_job_id(context)
        if job_id is None:
            return
        now_text = self._now_text()
        with self._lock:
            payload = self._ipc_jobs.get(job_id)
            if payload is None:
                return
            payload["status"] = "running"
            payload["queue_ahead"] = 0
            payload["progress"] = 0
            payload["message"] = "開始檢查"
            payload["updated_at"] = now_text

    def mark_context_progress(self, context: dict[str, str] | None, progress: int, message: str) -> None:
        """Mark progress for an external current context."""
        job_id = self._extract_external_job_id(context)
        if job_id is None:
            return
        now_text = self._now_text()
        with self._lock:
            payload = self._ipc_jobs.get(job_id)
            if payload is None:
                return
            payload["status"] = "running"
            payload["queue_ahead"] = 0
            payload["progress"] = max(0, min(100, int(progress)))
            payload["message"] = str(message)
            payload["updated_at"] = now_text

    def mark_context_finished(self, context: dict[str, str] | None, result_dicts: list[dict]) -> None:
        """Mark completion for an external current context."""
        job_id = self._extract_external_job_id(context)
        if job_id is None:
            return
        payload_result = self._build_bot_check_payload(result_dicts)
        now_text = self._now_text()
        with self._lock:
            payload = self._ipc_jobs.get(job_id)
            if payload is None:
                return
            payload["status"] = "completed"
            payload["queue_ahead"] = 0
            payload["progress"] = 100
            payload["message"] = "檢查完成"
            payload["result"] = payload_result
            payload["updated_at"] = now_text

    def mark_context_failed(self, context: dict[str, str] | None, message: str) -> None:
        """Mark failure for an external current context."""
        job_id = self._extract_external_job_id(context)
        if job_id is None:
            return
        now_text = self._now_text()
        with self._lock:
            payload = self._ipc_jobs.get(job_id)
            if payload is None:
                return
            payload["status"] = "failed"
            payload["queue_ahead"] = 0
            payload["progress"] = 0
            payload["message"] = str(message)
            payload["result"] = {
                "success": False,
                "has_updates": False,
                "lines": [f"執行失敗: {message}"],
                "results": [],
            }
            payload["updated_at"] = now_text

    def _extract_external_job_id(self, context: dict[str, str] | None) -> str | None:
        ctx = context or {}
        if ctx.get("type") != "external":
            return None
        job_id = str(ctx.get("job_id", "")).strip()
        if job_id == "":
            return None
        return job_id

    def _build_bot_check_payload(self, result_dicts: list[dict]) -> dict:
        has_updates = False
        lines: list[str] = []
        for item in result_dicts:
            item_success = bool(item.get("success", False))
            status_text = "成功" if item_success else "失敗"
            summary = item.get("summary")
            if isinstance(summary, dict):
                added = int(summary.get("added", 0))
                removed = int(summary.get("removed", 0))
                delta_text = f"新增 {added} / 刪除 {removed}"
                if item_success and (added > 0 or removed > 0):
                    has_updates = True
            else:
                delta_text = "無差異資料"
            lines.append(f"[{status_text}] {item.get('name', '')}: {item.get('message', '')} ({delta_text})")
        return {
            "success": True,
            "has_updates": has_updates,
            "lines": lines,
            "results": result_dicts,
        }

    def _now_text(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
