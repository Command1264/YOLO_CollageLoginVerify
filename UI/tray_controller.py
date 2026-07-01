from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QStyle, QSystemTrayIcon, QWidget


class LeftClickOnlyMenu(QMenu):
    """Tray menu that accepts left-click only."""

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            event.ignore()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            event.ignore()
            return
        super().mouseReleaseEvent(event)


class TrayController:
    """Create and manage system tray icon/menu wiring."""

    def __init__(self) -> None:
        self.tray_icon: QSystemTrayIcon | None = None
        self.tray_menu: QMenu | None = None

    def create_tray_icon(
        self,
        owner: QWidget,
        icon: QIcon,
        on_show_window: Callable[[], None],
        on_run_check: Callable[[], None],
        on_quit: Callable[[], None],
        on_activated: Callable[[QSystemTrayIcon.ActivationReason], None],
    ) -> QSystemTrayIcon | None:
        """Create tray icon and connect actions/callbacks."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = None
            self.tray_menu = None
            return None
        tray_icon = QSystemTrayIcon(icon, owner)
        tray_menu = LeftClickOnlyMenu(owner)
        show_action = QAction("顯示主視窗", owner)
        show_action.triggered.connect(on_show_window)
        run_action = QAction("立即檢查", owner)
        run_action.triggered.connect(on_run_check)
        quit_action = QAction("離開", owner)
        quit_action.triggered.connect(on_quit)
        tray_menu.addAction(show_action)
        tray_menu.addAction(run_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        tray_icon.setContextMenu(tray_menu)
        tray_icon.activated.connect(on_activated)
        tray_icon.show()
        self.tray_icon = tray_icon
        self.tray_menu = tray_menu
        return tray_icon

    def resolve_tray_icon(self, owner: QWidget, app_icon: QIcon | None, window_icon: QIcon) -> QIcon:
        """Resolve best tray icon with app icon and style fallback."""
        if app_icon is not None:
            return app_icon
        style = owner.style()
        pixmaps = [
            "SP_ComputerIcon",
            "SP_DesktopIcon",
            "SP_DriveHDIcon",
            "SP_FileIcon",
        ]
        for name in pixmaps:
            sp = getattr(QStyle.StandardPixmap, name, None)
            if sp is not None:
                return style.standardIcon(sp)
        return window_icon

    def hide_tray_icon(self) -> None:
        """Hide tray icon when app exits."""
        if self.tray_icon is None:
            return
        self.tray_icon.hide()
