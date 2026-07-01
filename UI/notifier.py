import json
import html
from dataclasses import dataclass, field
from pathlib import Path

import requests

from utils.app_paths import get_linked_users_path, get_runtime_base_dir, to_universal_path
from UI.diff_patch import trim_patch_for_message


@dataclass
class NotificationConfig:
    provider: str = "none"  # none / discord / telegram / both
    discord_bot_token: str = ""
    discord_linked_users_file: str = field(default_factory=lambda: to_universal_path(get_linked_users_path("discord")))
    telegram_token: str = ""
    telegram_linked_users_file: str = field(default_factory=lambda: to_universal_path(get_linked_users_path("telegram")))


class Notifier:
    def __init__(self, config: NotificationConfig, timeout: int = 15) -> None:
        self.config = config
        self.timeout = timeout

    def send_update(self, title: str, summary_text: str, patch_text: str) -> list[str]:
        """Send diff update to configured channels; returns error messages."""
        provider = self.config.provider.lower().strip()
        if provider == "none":
            return []

        discord_message = (
            f"{title}\n"
            f"{summary_text}\n"
            f"```diff\n{trim_patch_for_message(patch_text)}\n```"
        )
        telegram_message = (
            f"<b>{html.escape(title)}</b>\n"
            f"{html.escape(summary_text)}\n"
            f"<pre>{html.escape(trim_patch_for_message(patch_text))}</pre>"
        )

        errors: list[str] = []
        if provider in {"discord", "both"}:
            err = self._send_discord(discord_message)
            if err:
                errors.append(err)
        if provider in {"telegram", "both"}:
            err = self._send_telegram(telegram_message, parse_mode="HTML")
            if err:
                errors.append(err)
        return errors

    def send_text(self, message: str) -> list[str]:
        """Send plain text message to configured channels; returns error messages."""
        provider = self.config.provider.lower().strip()
        if provider == "none":
            return []
        errors: list[str] = []
        if provider in {"discord", "both"}:
            err = self._send_discord(message)
            if err:
                errors.append(err)
        if provider in {"telegram", "both"}:
            err = self._send_telegram(html.escape(message), parse_mode="HTML")
            if err:
                errors.append(err)
        return errors

    def _send_discord(self, message: str) -> str | None:
        if not self.config.discord_bot_token:
            return "Discord Bot Token 未設定"
        users = self._load_linked_users(self.config.discord_linked_users_file)
        if len(users) == 0:
            return "Discord 尚無訂閱者（請先使用 /link 完成綁定）"
        try:
            token = self.config.discord_bot_token
            headers = {
                "Authorization": f"Bot {token}",
                "Content-Type": "application/json",
            }
            failed = 0
            for user in users:
                recipient_id = user.get("user_id", "")
                if not recipient_id:
                    failed += 1
                    continue

                dm_response = requests.post(
                    "https://discord.com/api/v10/users/@me/channels",
                    headers=headers,
                    json={"recipient_id": recipient_id},
                    timeout=self.timeout,
                )
                if dm_response.status_code >= 300:
                    failed += 1
                    continue

                channel_id = dm_response.json().get("id")
                if not channel_id:
                    failed += 1
                    continue

                send_response = requests.post(
                    f"https://discord.com/api/v10/channels/{channel_id}/messages",
                    headers=headers,
                    json={"content": message},
                    timeout=self.timeout,
                )
                if send_response.status_code >= 300:
                    failed += 1

            if failed == len(users):
                return "Discord 發送失敗：所有訂閱者皆送出失敗"
            if failed > 0:
                return f"Discord 部分失敗：{failed}/{len(users)} 位訂閱者送出失敗"
            return None
        except Exception as exc:
            return f"Discord 發送例外: {exc}"

    def _send_telegram(self, message: str, parse_mode: str | None = None) -> str | None:
        if not self.config.telegram_token:
            return "Telegram Bot Token 未設定"
        users = self._load_linked_users(self.config.telegram_linked_users_file)
        if len(users) == 0:
            return "Telegram 尚無訂閱者（請先使用 /link 完成綁定）"
        try:
            failed = 0
            for user in users:
                chat_id = user.get("chat_id", "")
                if chat_id in ("", None):
                    failed += 1
                    continue
                response = requests.post(
                    f"https://api.telegram.org/bot{self.config.telegram_token}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": message,
                        "parse_mode": parse_mode,
                    },
                    timeout=self.timeout,
                )
                if response.status_code >= 300:
                    failed += 1

            if failed == len(users):
                return "Telegram 發送失敗：所有訂閱者皆送出失敗"
            if failed > 0:
                return f"Telegram 部分失敗：{failed}/{len(users)} 位訂閱者送出失敗"
            return None
        except Exception as exc:
            return f"Telegram 發送例外: {exc}"

    def _load_linked_users(self, file_path: str) -> list[dict]:
        path = Path(file_path)
        if not path.is_absolute():
            path = get_runtime_base_dir() / path
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError:
                return []
        if isinstance(data, dict):
            return list(data.values())
        if isinstance(data, list):
            return data
        return []
