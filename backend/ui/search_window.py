from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QAbstractItemView
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor


class SearchWorker(QThread):
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, query):
        super().__init__()
        self.query = query

    def run(self):
        try:
            from core.database import get_db_connection
            conn = get_db_connection()
            with conn.cursor() as cursor:
                like = f"%{self.query}%"
                sql = """
                    SELECT 
                        b.beneficiary_id,
                        b.lastname,
                        b.firstname,
                        b.middlename,
                        b.birthday,
                        b.gender,
                        s.site_name,
                        br.barangay_name,
                        b.registration_date,
                        CONCAT(u.firstname, ' ', u.lastname) AS created_by_name
                    FROM beneficiaries b
                    LEFT JOIN sites s ON b.site_id = s.site_id
                    LEFT JOIN barangays br ON s.barangay_code = br.barangay_code
                    LEFT JOIN users u ON b.created_by = u.user_id
                    WHERE b.deleted_at IS NULL
                      AND (
                        b.lastname LIKE %s OR
                        b.firstname LIKE %s OR
                        b.middlename LIKE %s OR
                        b.birthday LIKE %s OR
                        b.beneficiary_id LIKE %s
                      )
                    ORDER BY b.lastname, b.firstname
                    LIMIT 200
                """
                cursor.execute(sql, (like, like, like, like, like))
                self.finished.emit(cursor.fetchall())
            conn.close()
        except Exception as e:
            self.error.emit(str(e))


class SearchBeneficiaryWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Search Beneficiary")
        self.setMinimumSize(950, 600)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)

        # Center on screen
        screen = self.screen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Header
        lbl_title = QLabel("🔍  Beneficiary Search")
        lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(lbl_title)

        lbl_sub = QLabel("Search by name, birthday (YYYY-MM-DD), or ID.")
        lbl_sub.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        layout.addWidget(lbl_sub)

        # Search Bar
        search_layout = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Type a last name, first name, birthday, or beneficiary ID...")
        self.txt_search.setStyleSheet("""
            QLineEdit {
                padding: 8px 12px;
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                font-size: 14px;
            }
            QLineEdit:focus { border-color: #3498db; }
        """)
        self.txt_search.returnPressed.connect(self.do_search)

        self.btn_search = QPushButton("Search")
        self.btn_search.setFixedWidth(100)
        self.btn_search.setStyleSheet("""
            QPushButton {
                background-color: #2980b9;
                color: white;
                font-weight: bold;
                padding: 8px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #3498db; }
        """)
        self.btn_search.clicked.connect(self.do_search)

        search_layout.addWidget(self.txt_search)
        search_layout.addWidget(self.btn_search)
        layout.addLayout(search_layout)

        # Status label
        self.lbl_status = QLabel("Enter a search term above and press Search.")
        self.lbl_status.setStyleSheet("color: #95a5a6; font-size: 11px;")
        layout.addWidget(self.lbl_status)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #ecf0f1;")
        layout.addWidget(line)

        # Results Table
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "ID", "Last Name", "First Name", "Middle Name",
            "Birthday", "Gender", "Site", "Barangay",
            "Registered On", "Added By"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget { border: 1px solid #ecf0f1; font-size: 13px; }
            QHeaderView::section {
                background-color: #2c3e50;
                color: white;
                padding: 6px;
                font-weight: bold;
                border: none;
            }
            QTableWidget::item:selected { background-color: #d6eaf8; color: #2c3e50; }
        """)
        layout.addWidget(self.table)

        # Close button
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def do_search(self):
        query = self.txt_search.text().strip()
        if len(query) < 2:
            self.lbl_status.setText("⚠️  Please enter at least 2 characters.")
            return

        self.btn_search.setEnabled(False)
        self.btn_search.setText("Searching...")
        self.lbl_status.setText("Searching database...")
        self.table.setRowCount(0)

        self.worker = SearchWorker(query)
        self.worker.finished.connect(self.on_results)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def on_results(self, records):
        self.btn_search.setEnabled(True)
        self.btn_search.setText("Search")

        if not records:
            self.lbl_status.setText("❌  No beneficiaries found matching your search.")
            return

        self.lbl_status.setText(f"✅  Found {len(records)} result(s). {'(Showing top 200)' if len(records) == 200 else ''}")
        self.table.setRowCount(len(records))

        for row_idx, rec in enumerate(records):
            values = [
                rec.get('beneficiary_id', ''),
                rec.get('lastname', ''),
                rec.get('firstname', ''),
                rec.get('middlename', '') or '—',
                str(rec.get('birthday', '')),
                rec.get('gender', ''),
                rec.get('site_name', '') or '—',
                rec.get('barangay_name', '') or '—',
                str(rec.get('registration_date', '')),
                rec.get('created_by_name', '') or '—',
            ]
            for col_idx, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row_idx, col_idx, item)

    def on_error(self, err):
        self.btn_search.setEnabled(True)
        self.btn_search.setText("Search")
        self.lbl_status.setText(f"❌  Error: {err}")
        self.lbl_status.setStyleSheet("color: red; font-size: 11px;")
