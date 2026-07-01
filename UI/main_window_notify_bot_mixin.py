from __future__ import annotations

from UI.main_window_bot_runtime_mixin import MainWindowBotRuntimeMixin
from UI.main_window_notify_config_mixin import MainWindowNotifyConfigMixin


class MainWindowNotifyBotMixin(
    MainWindowNotifyConfigMixin,
    MainWindowBotRuntimeMixin,
):
    pass
