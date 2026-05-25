"""Controller for grid-based record actions extracted from MainWindow."""

from __future__ import annotations

from typing import Any


class RecordActionController:
    def __init__(self, main_window):
        self._win = main_window
        # delegate discrepancy-related actions to a dedicated controller
        from ui.controllers.discrepancy_action_controller import (
            DiscrepancyActionController,
        )

        self._discrepancy = DiscrepancyActionController(self._win)
        from ui.controllers.sync_controller import SyncController

        self._sync = SyncController(self._win)

    def on_grid_action(self, action_name: str, record: dict, action_widget: Any):
        return self._sync.handle_grid_action(action_name, record, action_widget)

    def on_missing_db_action(
        self, action_name: str, record_data: dict, action_widget: Any
    ):
        return self._discrepancy.on_missing_db_action(
            action_name, record_data, action_widget
        )

    def on_bday_action(self, action_name: str, record: dict, action_widget: Any):
        return self._discrepancy.on_bday_action(action_name, record, action_widget)

    def on_name_action(self, action_name: str, record: dict, action_widget: Any):
        return self._discrepancy.on_name_action(action_name, record, action_widget)

    def on_missing_excel_action(self, action: str, record: dict, widget: Any):
        return self._discrepancy.on_missing_excel_action(action, record, widget)
