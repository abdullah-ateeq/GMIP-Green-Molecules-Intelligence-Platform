"""Reusable source-selection dialog for GMIP market scans."""

from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from collectors.collector_manager import CollectorManager


class SourceSelectionDialog(QDialog):
    """
    Let the user select individual intelligence sources grouped by collector.

    The dialog does not run scans. It only returns the selected source IDs.
    """

    def __init__(
        self,
        parent=None,
        selected_source_ids: Iterable[str] | None = None,
    ):
        super().__init__(parent)

        self.setWindowTitle("Select Market Scan Sources")
        self.setModal(True)
        self.resize(620, 650)
        self.setMinimumSize(520, 500)

        self.manager = CollectorManager()
        self.source_checkboxes: dict[str, QCheckBox] = {}
        self.collector_checkboxes: dict[str, QCheckBox] = {}
        self.collector_source_ids: dict[str, list[str]] = {}

        self.initial_selected_source_ids = (
            None
            if selected_source_ids is None
            else set(selected_source_ids)
        )

        self._building_interface = True
        self._build_interface()
        self._apply_initial_selection()
        self._building_interface = False

        self._refresh_all_states()
        self._apply_styles()

    def _build_interface(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 22, 24, 22)
        main_layout.setSpacing(14)

        title = QLabel("Select Sources")
        title.setObjectName("dialogTitle")

        subtitle = QLabel(
            "Choose the official intelligence sources to include "
            "in this market scan."
        )
        subtitle.setObjectName("dialogSubtitle")
        subtitle.setWordWrap(True)

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)

        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(8)

        self.select_all_button = QPushButton("Select All")
        self.select_all_button.setObjectName("secondaryButton")
        self.select_all_button.clicked.connect(self.select_all_sources)

        self.clear_all_button = QPushButton("Clear All")
        self.clear_all_button.setObjectName("secondaryButton")
        self.clear_all_button.clicked.connect(self.clear_all_sources)

        controls_layout.addWidget(self.select_all_button)
        controls_layout.addWidget(self.clear_all_button)
        controls_layout.addStretch()

        self.selection_count_label = QLabel("0 sources selected")
        self.selection_count_label.setObjectName("selectionCount")
        controls_layout.addWidget(self.selection_count_label)

        main_layout.addLayout(controls_layout)

        separator = QFrame()
        separator.setObjectName("separator")
        separator.setFrameShape(QFrame.HLine)
        main_layout.addWidget(separator)

        scroll_area = QScrollArea()
        scroll_area.setObjectName("sourceScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)

        scroll_content = QWidget()
        scroll_content.setObjectName("scrollContent")
        self.collectors_layout = QVBoxLayout(scroll_content)
        self.collectors_layout.setContentsMargins(0, 0, 8, 0)
        self.collectors_layout.setSpacing(12)

        collectors = list(getattr(self.manager, "collectors", []))

        if not collectors:
            empty_label = QLabel("No collectors are currently registered.")
            empty_label.setObjectName("emptyState")
            empty_label.setAlignment(Qt.AlignCenter)
            self.collectors_layout.addWidget(empty_label)
        else:
            for collector in collectors:
                self._add_collector_group(collector)

        self.collectors_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area, 1)

        button_box = QDialogButtonBox(
            QDialogButtonBox.Cancel | QDialogButtonBox.Ok
        )
        button_box.setObjectName("dialogButtons")
        button_box.rejected.connect(self.reject)
        button_box.accepted.connect(self._accept_selection)

        apply_button = button_box.button(QDialogButtonBox.Ok)
        if apply_button is not None:
            apply_button.setText("Apply Selection")
            apply_button.setObjectName("applyButton")

        cancel_button = button_box.button(QDialogButtonBox.Cancel)
        if cancel_button is not None:
            cancel_button.setObjectName("cancelButton")

        main_layout.addWidget(button_box)

    def _add_collector_group(self, collector) -> None:
        collector_id = str(
            getattr(collector, "collector_id", "")
            or getattr(collector, "collector_name", "")
        )
        collector_name = str(
            getattr(collector, "collector_name", "")
            or collector_id
            or "Unnamed Collector"
        )

        group = QFrame()
        group.setObjectName("collectorGroup")

        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(16, 14, 16, 14)
        group_layout.setSpacing(9)

        collector_checkbox = QCheckBox(collector_name)
        collector_checkbox.setObjectName("collectorCheckbox")
        collector_checkbox.setTristate(True)
        collector_checkbox.stateChanged.connect(
            lambda state, cid=collector_id:
            self._handle_collector_state_changed(cid, state)
        )

        group_layout.addWidget(collector_checkbox)

        source_ids: list[str] = []

        for source in list(getattr(collector, "sources", [])):
            source_id = self._source_value(source, "source_id")
            source_name = (
                self._source_value(source, "source_name")
                or source_id
                or "Unnamed Source"
            )
            enabled = self._source_value(source, "enabled", True)

            if not source_id or enabled is False:
                continue

            source_checkbox = QCheckBox(str(source_name))
            source_checkbox.setObjectName("sourceCheckbox")
            source_checkbox.setProperty("sourceId", str(source_id))
            source_checkbox.stateChanged.connect(
                self._handle_source_state_changed
            )

            group_layout.addWidget(source_checkbox)
            self.source_checkboxes[str(source_id)] = source_checkbox
            source_ids.append(str(source_id))

        self.collector_checkboxes[collector_id] = collector_checkbox
        self.collector_source_ids[collector_id] = source_ids

        if not source_ids:
            no_sources_label = QLabel("No enabled sources")
            no_sources_label.setObjectName("noSourcesLabel")
            group_layout.addWidget(no_sources_label)
            collector_checkbox.setEnabled(False)

        self.collectors_layout.addWidget(group)

    @staticmethod
    def _source_value(source, key: str, default=None):
        if isinstance(source, dict):
            return source.get(key, default)
        return getattr(source, key, default)

    def _apply_initial_selection(self) -> None:
        if self.initial_selected_source_ids is None:
            selected_ids = set(self.source_checkboxes)
        else:
            selected_ids = self.initial_selected_source_ids

        for source_id, checkbox in self.source_checkboxes.items():
            checkbox.setChecked(source_id in selected_ids)

    def _handle_collector_state_changed(
        self,
        collector_id: str,
        state: int,
    ) -> None:
        if self._building_interface:
            return

        if state == Qt.PartiallyChecked:
            return

        should_check = state == Qt.Checked

        self._building_interface = True
        try:
            for source_id in self.collector_source_ids.get(
                collector_id,
                [],
            ):
                checkbox = self.source_checkboxes.get(source_id)
                if checkbox is not None:
                    checkbox.setChecked(should_check)
        finally:
            self._building_interface = False

        self._refresh_all_states()

    def _handle_source_state_changed(self, _state: int) -> None:
        if not self._building_interface:
            self._refresh_all_states()

    def _refresh_all_states(self) -> None:
        self._building_interface = True
        try:
            for collector_id in self.collector_checkboxes:
                self._refresh_collector_state(collector_id)
        finally:
            self._building_interface = False

        selected_count = len(self.selected_source_ids())
        total_count = len(self.source_checkboxes)

        noun = "source" if selected_count == 1 else "sources"
        self.selection_count_label.setText(
            f"{selected_count} of {total_count} {noun} selected"
        )

        button_box = self.findChild(
            QDialogButtonBox,
            "dialogButtons",
        )
        if button_box is not None:
            apply_button = button_box.button(QDialogButtonBox.Ok)
            if apply_button is not None:
                apply_button.setEnabled(selected_count > 0)

    def _refresh_collector_state(self, collector_id: str) -> None:
        collector_checkbox = self.collector_checkboxes.get(collector_id)
        source_ids = self.collector_source_ids.get(collector_id, [])

        if collector_checkbox is None or not source_ids:
            return

        checked_count = sum(
            self.source_checkboxes[source_id].isChecked()
            for source_id in source_ids
        )

        if checked_count == 0:
            collector_checkbox.setCheckState(Qt.Unchecked)
        elif checked_count == len(source_ids):
            collector_checkbox.setCheckState(Qt.Checked)
        else:
            collector_checkbox.setCheckState(Qt.PartiallyChecked)

    def select_all_sources(self) -> None:
        self._building_interface = True
        try:
            for checkbox in self.source_checkboxes.values():
                checkbox.setChecked(True)
        finally:
            self._building_interface = False

        self._refresh_all_states()

    def clear_all_sources(self) -> None:
        self._building_interface = True
        try:
            for checkbox in self.source_checkboxes.values():
                checkbox.setChecked(False)
        finally:
            self._building_interface = False

        self._refresh_all_states()

    def selected_source_ids(self) -> list[str]:
        """Return selected source IDs in collector display order."""
        return [
            source_id
            for source_id, checkbox in self.source_checkboxes.items()
            if checkbox.isChecked()
        ]

    def _accept_selection(self) -> None:
        if not self.selected_source_ids():
            return
        self.accept()

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QDialog {
                background-color: #F4F7FA;
            }

            QWidget {
                font-family: "Segoe UI";
                color: #172033;
            }

            #dialogTitle {
                font-size: 23px;
                font-weight: 700;
                color: #172033;
            }

            #dialogSubtitle {
                font-size: 12px;
                color: #728096;
            }

            #selectionCount {
                color: #11896D;
                font-size: 11px;
                font-weight: 700;
            }

            #separator {
                background-color: #DFE6ED;
                border: none;
                max-height: 1px;
            }

            #sourceScrollArea,
            #scrollContent {
                background-color: transparent;
            }

            #collectorGroup {
                background-color: white;
                border: 1px solid #E0E7ED;
                border-radius: 10px;
            }

            QCheckBox#collectorCheckbox {
                font-size: 14px;
                font-weight: 700;
                color: #26354A;
                spacing: 10px;
            }

            QCheckBox#sourceCheckbox {
                font-size: 12px;
                color: #4D5C70;
                spacing: 10px;
                margin-left: 24px;
                min-height: 24px;
            }

            QCheckBox::indicator {
                width: 17px;
                height: 17px;
            }

            #noSourcesLabel,
            #emptyState {
                color: #8290A2;
                font-size: 12px;
                padding: 18px;
            }

            QPushButton#secondaryButton {
                background-color: #EAF0F5;
                color: #315270;
                border: none;
                border-radius: 7px;
                padding: 8px 13px;
                font-size: 11px;
                font-weight: 700;
            }

            QPushButton#secondaryButton:hover {
                background-color: #DDE8F0;
            }

            QPushButton#applyButton {
                background-color: #11896D;
                color: white;
                border: none;
                border-radius: 7px;
                padding: 9px 18px;
                font-size: 12px;
                font-weight: 700;
            }

            QPushButton#applyButton:hover {
                background-color: #0E755E;
            }

            QPushButton#applyButton:disabled {
                background-color: #A9C8C0;
            }

            QPushButton#cancelButton {
                background-color: #E7EDF2;
                color: #42546A;
                border: none;
                border-radius: 7px;
                padding: 9px 18px;
                font-size: 12px;
                font-weight: 700;
            }

            QPushButton#cancelButton:hover {
                background-color: #DCE5EC;
            }
            """
        )
