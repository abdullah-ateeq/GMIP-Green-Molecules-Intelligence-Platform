from datetime import datetime

from PySide6.QtCore import QSettings, QTimer, Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from scan_worker import ScanWorker
from source_selection_dialog import SourceSelectionDialog

from database import (
    get_dashboard_summary,
    get_latest_changes,
    get_recent_opportunities,
    get_source_registry_status,
    sync_source_registry,
)

from gmip.config import SOURCE_REGISTRY


class KpiCard(QFrame):
    """Reusable dashboard KPI card."""

    def __init__(
        self,
        title: str,
        value: str,
        description: str,
        accent: str,
    ):
        super().__init__()

        self.setObjectName("kpiCard")
        self.setMinimumHeight(145)
        self.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(7)

        accent_bar = QFrame()
        accent_bar.setFixedHeight(5)
        accent_bar.setStyleSheet(
            f"""
            background-color: {accent};
            border-radius: 2px;
            """
        )

        title_label = QLabel(title)
        title_label.setObjectName("kpiTitle")

        self.value_label = QLabel(value)
        self.value_label.setObjectName("kpiValue")

        description_label = QLabel(description)
        description_label.setObjectName("kpiDescription")
        description_label.setWordWrap(True)

        layout.addWidget(accent_bar)
        layout.addSpacing(5)
        layout.addWidget(title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(description_label)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)


class PlaceholderPage(QWidget):
    """
    Temporary page used while the full module is being developed.
    """

    def __init__(
        self,
        title: str,
        description: str,
    ):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 34, 36, 34)
        layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setObjectName("pageTitle")

        description_label = QLabel(description)
        description_label.setObjectName("pageSubtitle")
        description_label.setWordWrap(True)

        message_box = QFrame()
        message_box.setObjectName("placeholderBox")

        message_layout = QVBoxLayout(message_box)
        message_layout.setContentsMargins(30, 30, 30, 30)

        message_title = QLabel("Module ready for development")
        message_title.setObjectName("placeholderTitle")
        message_title.setAlignment(Qt.AlignCenter)

        message_text = QLabel(
            "The application navigation is working. "
            "We will connect this page to live intelligence data "
            "during the next development steps."
        )
        message_text.setObjectName("placeholderText")
        message_text.setAlignment(Qt.AlignCenter)
        message_text.setWordWrap(True)

        message_layout.addStretch()
        message_layout.addWidget(message_title)
        message_layout.addWidget(message_text)
        message_layout.addStretch()

        layout.addWidget(title_label)
        layout.addWidget(description_label)
        layout.addSpacing(15)
        layout.addWidget(message_box)
        layout.addStretch()


class SourceMonitorPage(QWidget):
    """
    Source health / access-mode monitor backed by the SourceDefinition
    registry (gmip.config.SOURCE_REGISTRY).
    """

    def __init__(self):
        super().__init__()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(34, 28, 34, 28)
        main_layout.setSpacing(18)

        title_label = QLabel("Source Monitor")
        title_label.setObjectName("pageTitle")

        description_label = QLabel(
            "Review source availability, access mode and latest "
            "collection status."
        )
        description_label.setObjectName("pageSubtitle")
        description_label.setWordWrap(True)

        main_layout.addWidget(title_label)
        main_layout.addWidget(description_label)
        main_layout.addSpacing(6)

        panel = QFrame()
        panel.setObjectName("contentPanel")

        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(22, 20, 22, 20)
        panel_layout.setSpacing(14)

        self.sources_table = QTableWidget(0, 4)
        self.sources_table.setHorizontalHeaderLabels(
            ["Source", "Type", "Access Mode", "Status"]
        )
        self.sources_table.setEditTriggers(
            QAbstractItemView.NoEditTriggers
        )
        self.sources_table.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )
        self.sources_table.setSelectionMode(
            QAbstractItemView.SingleSelection
        )
        self.sources_table.setAlternatingRowColors(False)
        self.sources_table.verticalHeader().setVisible(False)
        self.sources_table.setShowGrid(False)
        self.sources_table.setFocusPolicy(Qt.NoFocus)

        self.sources_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch
        )
        for column in range(1, 4):
            self.sources_table.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.ResizeToContents
            )

        panel_layout.addWidget(self.sources_table)
        main_layout.addWidget(panel)
        main_layout.addStretch()

        self.refresh_data()

    def refresh_data(self) -> None:
        """Reload source health from SQLite, resyncing the registry first."""
        try:
            sync_source_registry(SOURCE_REGISTRY)
            rows = get_source_registry_status()

        except Exception as error:
            print("Source Monitor refresh failed:", error)
            rows = []

        self.sources_table.setRowCount(len(rows))

        for row_index, row in enumerate(rows):
            status_text = row.get("last_status") or (
                "Active" if row["enabled"] else "Inactive"
            )

            values = [
                row["source_name"],
                row["source_category"] or "",
                row["access_mode"],
                status_text,
            ]

            for column_index, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                self.sources_table.setItem(
                    row_index, column_index, item
                )


class DashboardPage(QWidget):
    """Executive dashboard backed by live SQLite data."""

    def __init__(self):
        super().__init__()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(34, 28, 34, 28)
        main_layout.setSpacing(22)

        banner = QFrame()
        banner.setObjectName("welcomeBanner")
        banner.setMinimumHeight(145)

        banner_layout = QHBoxLayout(banner)
        banner_layout.setContentsMargins(28, 22, 28, 22)

        banner_text_layout = QVBoxLayout()
        banner_text_layout.setSpacing(6)

        welcome_title = QLabel("Green Molecules Intelligence")
        welcome_title.setObjectName("welcomeTitle")

        welcome_text = QLabel(
            "Monitor global hydrogen, ammonia and methanol "
            "tenders, market developments and commercial "
            "opportunities from one intelligence workspace."
        )
        welcome_text.setObjectName("welcomeText")
        welcome_text.setWordWrap(True)
        welcome_text.setMaximumWidth(750)

        banner_text_layout.addWidget(welcome_title)
        banner_text_layout.addWidget(welcome_text)
        banner_layout.addLayout(banner_text_layout)
        banner_layout.addStretch()

        self.market_status = QLabel("●  MARKET MONITOR ACTIVE")
        self.market_status.setObjectName("marketStatus")
        banner_layout.addWidget(
            self.market_status,
            alignment=Qt.AlignTop,
        )

        main_layout.addWidget(banner)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)

        self.opportunities_card = KpiCard(
            "OPPORTUNITIES",
            "0",
            "Detected green molecule opportunities",
            "#1FB58F",
        )
        self.latest_changes_card = KpiCard(
            "LATEST CHANGES",
            "0",
            "Meaningful source updates requiring review",
            "#F2B84B",
        )
        self.monitored_sources_card = KpiCard(
            "MONITORED SOURCES",
            "0",
            "Official intelligence sources connected",
            "#4E8DF5",
        )
        self.last_scan_card = KpiCard(
            "LAST MARKET SCAN",
            "Never",
            "Latest collection status",
            "#8B6FF7",
        )

        cards_layout.addWidget(self.opportunities_card)
        cards_layout.addWidget(self.latest_changes_card)
        cards_layout.addWidget(self.monitored_sources_card)
        cards_layout.addWidget(self.last_scan_card)
        main_layout.addLayout(cards_layout)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(18)
        content_layout.addWidget(self.create_opportunities_panel(), 7)
        content_layout.addWidget(self.create_activity_panel(), 3)
        main_layout.addLayout(content_layout)

        self.refresh_data()

    def create_opportunities_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("contentPanel")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        header_layout = QHBoxLayout()
        title_layout = QVBoxLayout()
        title_layout.setSpacing(3)

        title = QLabel("Recent Opportunities")
        title.setObjectName("sectionTitle")
        subtitle = QLabel(
            "Relevant monitored sources requiring review"
        )
        subtitle.setObjectName("sectionSubtitle")

        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)

        view_all_button = QPushButton("View All")
        view_all_button.setObjectName("secondaryButton")
        view_all_button.setCursor(Qt.PointingHandCursor)

        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        header_layout.addWidget(view_all_button)
        layout.addLayout(header_layout)

        self.opportunities_table = QTableWidget(0, 5)
        self.opportunities_table.setHorizontalHeaderLabels(
            [
                "Opportunity",
                "Molecule",
                "Source",
                "Status",
                "Priority",
            ]
        )
        self.opportunities_table.setEditTriggers(
            QAbstractItemView.NoEditTriggers
        )
        self.opportunities_table.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )
        self.opportunities_table.setSelectionMode(
            QAbstractItemView.SingleSelection
        )
        self.opportunities_table.setAlternatingRowColors(False)
        self.opportunities_table.verticalHeader().setVisible(False)
        self.opportunities_table.setShowGrid(False)
        self.opportunities_table.setFocusPolicy(Qt.NoFocus)

        self.opportunities_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch
        )
        for column in range(1, 5):
            self.opportunities_table.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.ResizeToContents
            )

        layout.addWidget(self.opportunities_table)
        return panel

    def create_activity_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("contentPanel")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        title = QLabel("Latest Intelligence")
        title.setObjectName("sectionTitle")
        subtitle = QLabel("Recently detected market activity")
        subtitle.setObjectName("sectionSubtitle")

        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.activity_container = QWidget()
        self.activity_layout = QVBoxLayout(self.activity_container)
        self.activity_layout.setContentsMargins(0, 0, 0, 0)
        self.activity_layout.setSpacing(10)
        self.activity_layout.addStretch()

        layout.addWidget(self.activity_container)
        return panel

    def refresh_data(self) -> None:
        """Reload all dashboard content from SQLite."""
        try:
            summary = get_dashboard_summary()
            opportunities = get_recent_opportunities(limit=8)
            changes = get_latest_changes(limit=3)

            self.update_kpi_cards(summary)
            self.populate_opportunities(opportunities)
            self.populate_latest_intelligence(changes, summary)

            run_status = summary.get("run_status", "UNKNOWN")
            if run_status == "COMPLETED":
                self.market_status.setText("●  MARKET MONITOR ACTIVE")
            elif run_status == "COMPLETED_WITH_ERRORS":
                self.market_status.setText("●  SCAN COMPLETED WITH ERRORS")
            else:
                self.market_status.setText("●  MARKET MONITOR READY")

        except Exception as error:
            self.opportunities_card.set_value("Error")
            self.latest_changes_card.set_value("Error")
            self.monitored_sources_card.set_value("Error")
            self.last_scan_card.set_value("Unavailable")
            self.market_status.setText("●  DATABASE CONNECTION ERROR")
            print("Dashboard refresh failed:", error)

    def update_kpi_cards(self, summary: dict) -> None:
        self.opportunities_card.set_value(
            str(summary.get("opportunities", 0))
        )
        self.latest_changes_card.set_value(
            str(summary.get("latest_changes", 0))
        )
        self.monitored_sources_card.set_value(
            str(summary.get("monitored_sources", 0))
        )
        self.last_scan_card.set_value(
            self.format_datetime(summary.get("last_scan"))
        )

    def populate_opportunities(
        self,
        opportunities: list[dict],
    ) -> None:
        table = self.opportunities_table
        table.clearContents()
        table.setRowCount(len(opportunities))

        for row_index, opportunity in enumerate(opportunities):
            opportunity_name = (
                opportunity.get("page_title")
                or opportunity.get("source_name")
                or "Untitled Opportunity"
            )
            molecule = (
                opportunity.get("detected_products")
                or "Not classified"
            )
            source = opportunity.get("source_name") or "Unknown"
            status = self.format_status(
                opportunity.get("current_status")
            )
            priority = self.determine_priority(opportunity)

            row_values = [
                opportunity_name,
                molecule,
                source,
                status,
                priority,
            ]

            for column_index, value in enumerate(row_values):
                item = QTableWidgetItem(str(value))
                if column_index == 3:
                    item.setForeground(QColor("#11896D"))
                if column_index == 4 and value == "High":
                    item.setForeground(QColor("#C56A00"))
                table.setItem(row_index, column_index, item)

            table.setRowHeight(row_index, 52)

    def populate_latest_intelligence(
        self,
        changes: list[dict],
        summary: dict,
    ) -> None:
        while self.activity_layout.count() > 1:
            item = self.activity_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        activities = []
        for change in changes:
            category = (
                change.get("change_type") or "MARKET UPDATE"
            ).replace("_", " ").upper()
            activity_title = (
                change.get("source_name")
                or "Monitored source changed"
            )
            activity_text = (
                change.get("change_summary")
                or "A meaningful source update was detected."
            )
            activities.append(
                (
                    category,
                    activity_title,
                    activity_text,
                    "#F2B84B",
                )
            )

        if not activities:
            activities.append(
                (
                    "SOURCE SCAN",
                    "No recent changes detected",
                    (
                        f'{summary.get("sources_checked", 0)} '
                        "sources were included in the latest scan."
                    ),
                    "#1FB58F",
                )
            )

        for activity_data in activities:
            activity = self.create_activity_item(*activity_data)
            self.activity_layout.insertWidget(
                self.activity_layout.count() - 1,
                activity,
            )

    def create_activity_item(
        self,
        category: str,
        activity_title: str,
        activity_text: str,
        accent: str,
    ) -> QFrame:
        activity = QFrame()
        activity.setObjectName("activityItem")

        activity_layout = QHBoxLayout(activity)
        activity_layout.setContentsMargins(12, 12, 12, 12)
        activity_layout.setSpacing(12)

        indicator = QFrame()
        indicator.setFixedWidth(5)
        indicator.setStyleSheet(
            f"""
            background-color: {accent};
            border-radius: 2px;
            """
        )

        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)

        category_label = QLabel(category)
        category_label.setObjectName("activityCategory")
        title_label = QLabel(activity_title)
        title_label.setObjectName("activityTitle")
        text_label = QLabel(activity_text)
        text_label.setObjectName("activityText")
        text_label.setWordWrap(True)

        text_layout.addWidget(category_label)
        text_layout.addWidget(title_label)
        text_layout.addWidget(text_label)
        activity_layout.addWidget(indicator)
        activity_layout.addLayout(text_layout)

        return activity

    @staticmethod
    def format_status(status: str | None) -> str:
        if not status:
            return "Monitoring"
        return status.replace("_", " ").title()

    @staticmethod
    def determine_priority(opportunity: dict) -> str:
        status = (
            opportunity.get("current_status") or ""
        ).upper()
        return "High" if status == "CHANGED" else "Medium"

    @staticmethod
    def format_datetime(value: str | None) -> str:
        if not value:
            return "Never"
        try:
            parsed = datetime.fromisoformat(value)
            return parsed.strftime("%d %b %Y\n%H:%M")
        except ValueError:
            return value


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle(
            "Green Molecules Intelligence Platform"
        )
        self.resize(1500, 920)
        self.setMinimumSize(1200, 760)

        self.navigation_buttons = []
        self.scan_worker: ScanWorker | None = None
        self.scan_animation_timer = QTimer(self)
        self.scan_animation_timer.setInterval(450)
        self.scan_animation_timer.timeout.connect(
            self.update_scan_animation
        )
        self.scan_animation_step = 0

        self.settings = QSettings(
            "GMIP",
            "GreenMoleculesIntelligencePlatform",
        )
        self.available_source_ids = self.get_available_source_ids()
        self.selected_source_ids = self.load_selected_source_ids()

        self.build_interface()
        self.apply_styles()
        self.open_page(0)

    def build_interface(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        application_layout = QHBoxLayout(
            central_widget
        )
        application_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        application_layout.setSpacing(0)

        sidebar = self.create_sidebar()

        right_side = QWidget()
        right_side.setObjectName("rightSide")

        right_layout = QVBoxLayout(right_side)
        right_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        right_layout.setSpacing(0)

        header = self.create_header()

        self.page_stack = QStackedWidget()

        self.dashboard_page = DashboardPage()
        self.page_stack.addWidget(self.dashboard_page)

        self.page_stack.addWidget(
            PlaceholderPage(
                "Opportunities",
                "Explore and assess global tenders, "
                "offtake programmes and molecule "
                "supply opportunities.",
            )
        )

        self.page_stack.addWidget(
            PlaceholderPage(
                "Latest Changes",
                "Review meaningful changes detected "
                "across monitored official sources.",
            )
        )

        self.page_stack.addWidget(
            PlaceholderPage(
                "Market News",
                "Track commercial, policy and market "
                "announcements affecting green molecules.",
            )
        )

        self.page_stack.addWidget(SourceMonitorPage())

        self.page_stack.addWidget(
            PlaceholderPage(
                "Reports",
                "Access intelligence summaries, exports "
                "and management-ready reports.",
            )
        )

        self.page_stack.addWidget(
            PlaceholderPage(
                "Settings",
                "Manage monitored sources, products, "
                "keywords and application preferences.",
            )
        )

        right_layout.addWidget(header)
        right_layout.addWidget(self.page_stack)

        application_layout.addWidget(sidebar)
        application_layout.addWidget(right_side)

    def create_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(255)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 22, 18, 22)
        layout.setSpacing(8)

        brand = QLabel("GMIP")
        brand.setObjectName("brand")

        brand_title = QLabel(
            "Green Molecules\nIntelligence Platform"
        )
        brand_title.setObjectName("brandTitle")

        brand_subtitle = QLabel(
            "Tender & Market Intelligence"
        )
        brand_subtitle.setObjectName(
            "brandSubtitle"
        )

        layout.addWidget(brand)
        layout.addWidget(brand_title)
        layout.addWidget(brand_subtitle)
        layout.addSpacing(28)

        navigation_items = [
            ("⌂", "Dashboard"),
            ("◎", "Opportunities"),
            ("↻", "Latest Changes"),
            ("▤", "Market News"),
            ("◉", "Source Monitor"),
            ("▥", "Reports"),
            ("⚙", "Settings"),
        ]

        for index, (icon, label) in enumerate(
            navigation_items
        ):
            button = QPushButton(
                f"{icon}    {label}"
            )

            button.setObjectName(
                "navigationButton"
            )
            button.setCheckable(True)
            button.setCursor(
                Qt.PointingHandCursor
            )
            button.setMinimumHeight(48)

            button.clicked.connect(
                lambda checked=False, page=index:
                self.open_page(page)
            )

            self.navigation_buttons.append(
                button
            )

            layout.addWidget(button)

        layout.addStretch()

        footer_line = QFrame()
        footer_line.setObjectName("sidebarLine")
        footer_line.setFixedHeight(1)

        version = QLabel("Prototype Version 1.0")
        version.setObjectName("versionLabel")

        status = QLabel("●  Intelligence Engine Online")
        status.setObjectName("sidebarStatus")

        layout.addWidget(footer_line)
        layout.addSpacing(8)
        layout.addWidget(status)
        layout.addWidget(version)

        return sidebar

    def create_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("header")
        header.setFixedHeight(88)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(32, 16, 32, 16)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)

        self.header_title = QLabel("Dashboard")
        self.header_title.setObjectName("headerTitle")

        header_subtitle = QLabel(
            "Global Tender & Market Intelligence"
        )
        header_subtitle.setObjectName(
            "headerSubtitle"
        )

        title_layout.addWidget(self.header_title)
        title_layout.addWidget(header_subtitle)

        self.source_selection_button = QPushButton()
        self.source_selection_button.setObjectName(
            "sourceSelectionButton"
        )
        self.source_selection_button.setCursor(
            Qt.PointingHandCursor
        )
        self.source_selection_button.setMinimumSize(190, 46)
        self.source_selection_button.clicked.connect(
            self.open_source_selection_dialog
        )
        self.update_source_selection_summary()

        self.scan_button = QPushButton(
            "↻  Run Market Scan"
        )
        self.scan_button.setObjectName("scanButton")
        self.scan_button.setCursor(Qt.PointingHandCursor)
        self.scan_button.setMinimumSize(180, 46)

        self.scan_button.clicked.connect(
            self.start_market_scan
        )

        layout.addLayout(title_layout)
        layout.addStretch()
        layout.addWidget(self.source_selection_button)
        layout.addSpacing(10)
        layout.addWidget(self.scan_button)

        return header

    @staticmethod
    def _source_value(source, key: str, default=None):
        if isinstance(source, dict):
            return source.get(key, default)
        return getattr(source, key, default)

    def get_available_source_ids(self) -> list[str]:
        """Return enabled source IDs in collector display order."""
        try:
            from collectors.collector_manager import CollectorManager

            manager = CollectorManager()
            source_ids: list[str] = []

            for collector in getattr(manager, "collectors", []):
                for source in getattr(collector, "sources", []):
                    source_id = self._source_value(
                        source,
                        "source_id",
                    )
                    enabled = self._source_value(
                        source,
                        "enabled",
                        True,
                    )

                    if source_id and enabled is not False:
                        source_ids.append(str(source_id))

            return source_ids

        except Exception as error:
            print("Could not load available source IDs:", error)
            return []

    def load_selected_source_ids(self) -> list[str]:
        """Load and validate the user's last saved scan selection."""
        saved_value = self.settings.value(
            "scan/selected_source_ids",
            None,
        )

        if saved_value is None:
            return list(self.available_source_ids)

        if isinstance(saved_value, str):
            saved_ids = [
                value
                for value in saved_value.split("|")
                if value
            ]
        else:
            saved_ids = [
                str(value)
                for value in saved_value
            ]

        available_set = set(self.available_source_ids)
        validated_ids = [
            source_id
            for source_id in saved_ids
            if source_id in available_set
        ]

        return validated_ids or list(self.available_source_ids)

    def save_selected_source_ids(self) -> None:
        self.settings.setValue(
            "scan/selected_source_ids",
            "|".join(self.selected_source_ids),
        )

    def update_source_selection_summary(self) -> None:
        if not hasattr(self, "source_selection_button"):
            return

        selected_count = len(self.selected_source_ids)
        total_count = len(self.available_source_ids)

        if selected_count == total_count and total_count:
            button_text = f"All Sources ({total_count})  ▾"
        else:
            noun = "Source" if selected_count == 1 else "Sources"
            button_text = f"{selected_count} {noun} Selected  ▾"

        self.source_selection_button.setText(button_text)
        self.scan_button.setEnabled(selected_count > 0) \
            if hasattr(self, "scan_button") else None

    def open_source_selection_dialog(self) -> None:
        if self.scan_worker is not None and self.scan_worker.isRunning():
            return

        dialog = SourceSelectionDialog(
            self,
            selected_source_ids=self.selected_source_ids,
        )

        if dialog.exec() == QDialog.Accepted:
            self.selected_source_ids = dialog.selected_source_ids()
            self.save_selected_source_ids()
            self.update_source_selection_summary()

    def open_page(self, index: int):
        page_names = [
            "Dashboard",
            "Opportunities",
            "Latest Changes",
            "Market News",
            "Source Monitor",
            "Reports",
            "Settings",
        ]

        self.page_stack.setCurrentIndex(index)
        self.header_title.setText(
            page_names[index]
        )

        for button_index, button in enumerate(
            self.navigation_buttons
        ):
            button.setChecked(
                button_index == index
            )

    def start_market_scan(self) -> None:
        """Start the real collector in a background thread."""
        if self.scan_worker is not None and self.scan_worker.isRunning():
            return

        if not self.selected_source_ids:
            QMessageBox.warning(
                self,
                "No Sources Selected",
                "Select at least one intelligence source before "
                "starting the market scan.",
            )
            return

        self.scan_button.setEnabled(False)
        self.source_selection_button.setEnabled(False)
        self.scan_animation_step = 0
        self.scan_button.setText("Scanning")
        self.scan_animation_timer.start()
        self.dashboard_page.market_status.setText(
            "●  MARKET SCAN IN PROGRESS"
        )

        self.scan_worker = ScanWorker(
            self,
            selected_source_ids=list(self.selected_source_ids),
        )
        self.scan_worker.scan_completed.connect(
            self.handle_scan_completed
        )
        self.scan_worker.scan_failed.connect(
            self.handle_scan_failed
        )
        self.scan_worker.finished.connect(
            self.release_scan_worker
        )
        self.scan_worker.start()

    def update_scan_animation(self) -> None:
        """Animate the scan button while collection is running."""
        self.scan_animation_step = (
            self.scan_animation_step + 1
        ) % 4
        dots = "." * self.scan_animation_step
        self.scan_button.setText(f"Scanning{dots}")

    def handle_scan_completed(self, summary: dict) -> None:
        """Refresh live data and show a concise scan summary."""
        self.scan_animation_timer.stop()
        self.dashboard_page.refresh_data()

        errors_count = int(summary.get("errors_count", 0))
        if errors_count:
            self.scan_button.setText("⚠  Scan Completed")
        else:
            self.scan_button.setText("✓  Scan Completed")

        duration = self.format_duration(
            float(summary.get("duration_seconds", 0.0))
        )

        message = QMessageBox(self)
        message.setWindowTitle("Market Scan Completed")
        message.setIcon(
            QMessageBox.Warning
            if errors_count
            else QMessageBox.Information
        )
        message.setText("The market scan has finished.")
        message.setInformativeText(
            "Sources checked: "
            f'{summary.get("sources_checked", 0)}\n'
            "Changes detected: "
            f'{summary.get("sources_changed", 0)}\n'
            "New baselines: "
            f'{summary.get("new_baselines", 0)}\n'
            "Errors: "
            f"{errors_count}\n"
            "Duration: "
            f"{duration}"
        )
        message.setStandardButtons(QMessageBox.Ok)
        message.exec()

        QTimer.singleShot(1800, self.restore_scan_button)

    def handle_scan_failed(self, error_message: str) -> None:
        """Restore the interface and report an unexpected failure."""
        self.scan_animation_timer.stop()
        self.scan_button.setText("✕  Scan Failed")
        self.dashboard_page.refresh_data()
        self.dashboard_page.market_status.setText(
            "●  MARKET SCAN FAILED"
        )

        QMessageBox.critical(
            self,
            "Market Scan Failed",
            "The market scan could not be completed.\n\n"
            f"Details: {error_message}",
        )

        QTimer.singleShot(2500, self.restore_scan_button)

    def restore_scan_button(self) -> None:
        self.scan_button.setText("↻  Run Market Scan")
        self.scan_button.setEnabled(
            bool(self.selected_source_ids)
        )
        self.source_selection_button.setEnabled(True)
        self.update_source_selection_summary()

    def release_scan_worker(self) -> None:
        if self.scan_worker is not None:
            self.scan_worker.deleteLater()
            self.scan_worker = None

    @staticmethod
    def format_duration(seconds: float) -> str:
        total_seconds = max(0, int(round(seconds)))
        minutes, remaining_seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)

        if hours:
            return f"{hours:02d}:{minutes:02d}:{remaining_seconds:02d}"
        return f"{minutes:02d}:{remaining_seconds:02d}"

    def apply_styles(self):
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #F4F7FA;
            }

            QWidget {
                font-family: "Segoe UI";
                color: #172033;
            }

            #sidebar {
                background-color: #0A2342;
                border: none;
            }

            #brand {
                color: #41D3A2;
                font-size: 13px;
                font-weight: 800;
                letter-spacing: 2px;
            }

            #brandTitle {
                color: white;
                font-size: 20px;
                font-weight: 700;
                line-height: 1.3;
            }

            #brandSubtitle {
                color: #9FB1C5;
                font-size: 11px;
            }

            QPushButton#navigationButton {
                background-color: transparent;
                color: #B9C7D6;
                border: none;
                border-radius: 8px;
                text-align: left;
                padding-left: 16px;
                font-size: 14px;
                font-weight: 600;
            }

            QPushButton#navigationButton:hover {
                background-color: #12365C;
                color: white;
            }

            QPushButton#navigationButton:checked {
                background-color: #16446F;
                color: white;
                border-left: 4px solid #41D3A2;
            }

            #sidebarLine {
                background-color: #284866;
            }

            #sidebarStatus {
                color: #41D3A2;
                font-size: 11px;
                font-weight: 600;
            }

            #versionLabel {
                color: #71869C;
                font-size: 10px;
            }

            #rightSide {
                background-color: #F4F7FA;
            }

            #header {
                background-color: white;
                border-bottom: 1px solid #DFE6ED;
            }

            #headerTitle {
                font-size: 22px;
                font-weight: 700;
                color: #172033;
            }

            #headerSubtitle {
                font-size: 12px;
                color: #728096;
            }

            QPushButton#sourceSelectionButton {
                background-color: #EEF3F7;
                color: #315270;
                border: 1px solid #D6E0E8;
                border-radius: 8px;
                padding: 0 16px;
                font-size: 12px;
                font-weight: 700;
            }

            QPushButton#sourceSelectionButton:hover {
                background-color: #E1EAF1;
                border: 1px solid #C7D4DF;
            }

            QPushButton#sourceSelectionButton:disabled {
                background-color: #F2F5F7;
                color: #9AA7B5;
                border: 1px solid #E1E7EC;
            }

            QPushButton#scanButton {
                background-color: #11896D;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 0 18px;
                font-size: 13px;
                font-weight: 700;
            }

            QPushButton#scanButton:hover {
                background-color: #0E755E;
            }

            QPushButton#scanButton:disabled {
                background-color: #82B9AA;
            }

            #welcomeBanner {
                background-color: #0E3156;
                border-radius: 12px;
            }

            #welcomeTitle {
                color: white;
                font-size: 27px;
                font-weight: 700;
            }

            #welcomeText {
                color: #C6D5E4;
                font-size: 14px;
                line-height: 1.5;
            }

            #marketStatus {
                background-color: #153F68;
                color: #41D3A2;
                border-radius: 14px;
                padding: 9px 13px;
                font-size: 11px;
                font-weight: 700;
            }

            #kpiCard,
            #contentPanel {
                background-color: white;
                border: 1px solid #E2E8EE;
                border-radius: 11px;
            }

            #kpiCard:hover {
                border: 1px solid #BFCBD7;
            }

            #kpiTitle {
                color: #78869A;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1px;
            }

            #kpiValue {
                color: #172033;
                font-size: 29px;
                font-weight: 750;
            }

            #kpiDescription {
                color: #8390A3;
                font-size: 11px;
            }

            #sectionTitle {
                color: #172033;
                font-size: 17px;
                font-weight: 700;
            }

            #sectionSubtitle {
                color: #8591A2;
                font-size: 11px;
            }

            QPushButton#secondaryButton {
                background-color: #EEF3F7;
                color: #315270;
                border: none;
                border-radius: 7px;
                padding: 9px 14px;
                font-size: 11px;
                font-weight: 700;
            }

            QPushButton#secondaryButton:hover {
                background-color: #E1EAF1;
            }

            QTableWidget {
                background-color: white;
                border: none;
                font-size: 12px;
                selection-background-color: #E8F4F1;
                selection-color: #172033;
            }

            QHeaderView::section {
                background-color: #F4F7F9;
                color: #657386;
                border: none;
                border-bottom: 1px solid #E1E7EC;
                padding: 11px;
                font-size: 11px;
                font-weight: 700;
            }

            QTableWidget::item {
                border-bottom: 1px solid #EEF1F4;
                padding: 8px;
            }

            #activityItem {
                background-color: #F8FAFC;
                border: 1px solid #E8EDF2;
                border-radius: 8px;
            }

            #activityCategory {
                color: #7A8799;
                font-size: 9px;
                font-weight: 800;
                letter-spacing: 1px;
            }

            #activityTitle {
                color: #26354A;
                font-size: 12px;
                font-weight: 700;
            }

            #activityText {
                color: #7C899A;
                font-size: 10px;
            }

            #pageTitle {
                color: #172033;
                font-size: 26px;
                font-weight: 700;
            }

            #pageSubtitle {
                color: #78869A;
                font-size: 13px;
            }

            #placeholderBox {
                background-color: white;
                border: 1px solid #E0E7ED;
                border-radius: 12px;
                min-height: 420px;
            }

            #placeholderTitle {
                color: #315270;
                font-size: 19px;
                font-weight: 700;
            }

            #placeholderText {
                color: #8290A2;
                font-size: 13px;
            }
            """
        )