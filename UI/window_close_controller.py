from __future__ import annotations

from collections.abc import Callable


class WindowCloseController:
    """Handle app quit and window close flow orchestration."""

    def quit_app(
        self,
        set_force_exit: Callable[[], None],
        stop_captcha_server: Callable[[], None],
        stop_check_ipc_server: Callable[[], None],
        stop_all_bots: Callable[[], None],
        release_instance_lock: Callable[[], None],
        hide_tray_icon: Callable[[], None],
        quit_application: Callable[[], None],
    ) -> None:
        """Perform full application quit sequence."""
        set_force_exit()
        stop_captcha_server()
        stop_check_ipc_server()
        stop_all_bots()
        release_instance_lock()
        hide_tray_icon()
        quit_application()

    def handle_close_event(
        self,
        force_exit: bool,
        has_tray_icon: bool,
        stop_captcha_server: Callable[[], None],
        stop_check_ipc_server: Callable[[], None],
        stop_all_bots: Callable[[], None],
        release_instance_lock: Callable[[], None],
        accept_event: Callable[[], None],
        ignore_event: Callable[[], None],
        hide_window: Callable[[], None],
        show_minimize_message: Callable[[], None],
    ) -> None:
        """Handle close event by either quitting or minimizing to tray."""
        if force_exit or (not has_tray_icon):
            stop_captcha_server()
            stop_check_ipc_server()
            stop_all_bots()
            release_instance_lock()
            accept_event()
            return
        ignore_event()
        hide_window()
        show_minimize_message()
