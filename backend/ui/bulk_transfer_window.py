from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QAbstractItemView, QMessageBox, QCheckBox, QWidget
)
from PySide6.QtCore import Qt
import datetime


class BulkTransferWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bulk Transfer Beneficiaries")
        self.setMinimumSize(820, 520)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)

        # Center on screen
        screen = self.screen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

        self.sites = []
        self.beneficiaries = []

        self.setup_ui()
        self.load_sites()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header Section
        header_layout = QHBoxLayout()
        lbl_title = QLabel("📦  Bulk Feeding Site Relocation")
        lbl_title.setStyleSheet("font-size: 18px; font-weight: bold;")
        lbl_title.setWordWrap(True)
        header_layout.addWidget(lbl_title)
        
        lbl_sub = QLabel("Select a source site, select multiple beneficiaries, and transfer them in one batch.")
        lbl_sub.setStyleSheet("font-size: 12px; margin-top: 2px;")
        lbl_sub.setWordWrap(True)
        
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_sub)

        # Top Control Frame - Source Site Selection
        src_frame = QFrame()
        src_frame.setStyleSheet("""
            QFrame {
                border-radius: 6px;
            }
        """)
        src_layout = QHBoxLayout(src_frame)
        src_layout.setContentsMargins(15, 10, 15, 10)

        lbl_src = QLabel("Source Feeding Site:")
        lbl_src.setStyleSheet("font-weight: bold; font-size: 13px; border: none;")
        
        self.cmb_source = QComboBox()
        self.cmb_source.setMinimumWidth(350)
        self.cmb_source.currentIndexChanged.connect(self.on_source_site_changed)

        src_layout.addWidget(lbl_src)
        src_layout.addWidget(self.cmb_source)
        src_layout.addStretch()
        
        layout.addWidget(src_frame)

        # Status / Instructions Label
        self.lbl_status = QLabel("Please select a source feeding site above.")
        self.lbl_status.setStyleSheet("font-size: 12px; font-weight: bold;")
        self.lbl_status.setWordWrap(True)
        layout.addWidget(self.lbl_status)

        # Beneficiaries Grid
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Select", "ID", "Last Name", "First Name", "Middle Name",
            "Birthday", "Gender", "Registered On"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.setWordWrap(False)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.verticalHeader().setDefaultSectionSize(28)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setAlternatingRowColors(True)
        self.table.itemChanged.connect(self.update_action_state)
        layout.addWidget(self.table)

        # Bottom Control Panel - Target Selection & Relocate Action
        dest_frame = QFrame()
        dest_frame.setStyleSheet("""
            QFrame {
                border-radius: 6px;
            }
        """)
        dest_layout = QHBoxLayout(dest_frame)
        dest_layout.setContentsMargins(15, 12, 15, 12)

        lbl_dest = QLabel("Target Feeding Site:")
        lbl_dest.setStyleSheet("font-weight: bold; font-size: 13px; border: none;")

        self.cmb_target = QComboBox()
        self.cmb_target.setMinimumWidth(350)

        self.btn_transfer = QPushButton("📦 Transfer Selected Beneficiary(ies)")
        self.btn_transfer.setEnabled(False)
        self.btn_transfer.setStyleSheet("""
            QPushButton {
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #d35400; }
            QPushButton:disabled { background-color: #bdc3c7; color: #7f8c8d; }
        """)
        self.btn_transfer.clicked.connect(self.on_transfer_clicked)

        dest_layout.addWidget(lbl_dest)
        dest_layout.addWidget(self.cmb_target)
        dest_layout.addSpacing(10)
        dest_layout.addWidget(self.btn_transfer)
        dest_layout.addStretch()

        layout.addWidget(dest_frame)

        # Action Buttons Layout (Close)
        btn_box = QHBoxLayout()
        btn_close = QPushButton("Close")
        btn_close.setFixedWidth(100)
        btn_close.clicked.connect(self.accept)
        btn_box.addStretch()
        btn_box.addWidget(btn_close)
        
        layout.addLayout(btn_box)

    def load_sites(self):
        from core.database import get_sites
        self.sites = get_sites()
        
        # Populate comboboxes
        self.cmb_source.blockSignals(True)
        self.cmb_source.clear()
        self.cmb_source.addItem(" -- Choose Source Site -- ", userData=None)
        
        for s in self.sites:
            batch_str = f" - Batch {s['batch']}" if s.get('batch') else ""
            display_text = f"{s['site_name']} ({s['barangay_name']}){batch_str}"
            self.cmb_source.addItem(display_text, userData=s['site_id'])
            
        self.cmb_source.blockSignals(False)
        self.update_target_combobox(None)

    def update_target_combobox(self, exclude_site_id):
        self.cmb_target.clear()
        
        count = 0
        for s in self.sites:
            if s['site_id'] != exclude_site_id:
                batch_str = f" - Batch {s['batch']}" if s.get('batch') else ""
                display_text = f"{s['site_name']} ({s['barangay_name']}){batch_str}"
                self.cmb_target.addItem(display_text, userData=s['site_id'])
                count += 1
                
        if count == 0:
            self.cmb_target.addItem("No alternative sites available", userData=None)
            self.cmb_target.setEnabled(False)
        else:
            self.cmb_target.setEnabled(True)

    def on_source_site_changed(self, index):
        source_site_id = self.cmb_source.currentData()
        self.table.setRowCount(0)
        self.btn_transfer.setEnabled(False)

        if not source_site_id:
            self.lbl_status.setText("Please select a source feeding site above.")
            self.update_target_combobox(None)
            return

        self.update_target_combobox(source_site_id)
        self.load_beneficiaries(source_site_id)

    def load_beneficiaries(self, site_id):
        from core.database import get_beneficiaries_by_site
        self.lbl_status.setText("Loading beneficiaries...")
        
        try:
            records = get_beneficiaries_by_site(site_id)
            self.beneficiaries = records
            
            if not records:
                self.lbl_status.setText("❌ No active beneficiaries registered at this feeding site.")
                return

            self.lbl_status.setText(
                f"✅ Found {len(records)} active beneficiary(ies) at this site. "
                "Select one or more from the list to relocate them."
            )
            self.table.setRowCount(len(records))

            self.table.blockSignals(True)
            for row_idx, rec in enumerate(records):
                chk_widget = QWidget()
                chk_layout = QHBoxLayout(chk_widget)
                chk_layout.setContentsMargins(0, 0, 0, 0)
                chk_layout.setAlignment(Qt.AlignCenter)
                
                chk_box = QCheckBox()
                chk_box.stateChanged.connect(lambda state: self.update_action_state())
                chk_layout.addWidget(chk_box)
                self.table.setCellWidget(row_idx, 0, chk_widget)
                
                values = [
                    rec.get('beneficiary_id', ''),
                    rec.get('lastname', ''),
                    rec.get('firstname', ''),
                    rec.get('middlename', '') or '—',
                    str(rec.get('birthday', '')),
                    rec.get('gender', ''),
                    str(rec.get('registration_date', ''))
                ]
                for col_idx, val in enumerate(values):
                    item = QTableWidgetItem(str(val))
                    if col_idx in (1, 2, 3):  # Last Name, First Name, Middle Name
                        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    else:
                        item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row_idx, col_idx + 1, item)
            self.table.blockSignals(False)
            self.table.resizeColumnsToContents()
            self.update_action_state()
        except Exception as e:
            self.lbl_status.setText(f"❌ Error loading records: {e}")
            QMessageBox.critical(self, "Database Error", f"Failed to query beneficiaries:\n{e}")

    def get_selected_rows(self):
        selected_rows = []
        for i in range(self.table.rowCount()):
            widget = self.table.cellWidget(i, 0)
            if widget:
                chk_box = widget.findChild(QCheckBox)
                if chk_box and chk_box.isChecked():
                    selected_rows.append(i)
        return selected_rows

    def update_action_state(self, item=None):
        selected_rows = self.get_selected_rows()
        has_selection = len(selected_rows) > 0
        has_target = self.cmb_target.currentData() is not None
        self.btn_transfer.setEnabled(has_selection and has_target)

    def on_transfer_clicked(self):
        selected_rows = self.get_selected_rows()
        
        if not selected_rows:
            return

        target_site_id = self.cmb_target.currentData()
        target_site_name = self.cmb_target.currentText()
        if not target_site_id:
            QMessageBox.warning(self, "No Target Site", "Please select a target feeding site.")
            return

        # Gather beneficiary IDs and names
        beneficiary_ids = []
        beneficiary_names = []
        for r in selected_rows:
            id_item = self.table.item(r, 1)
            ln_item = self.table.item(r, 2)
            fn_item = self.table.item(r, 3)
            if id_item:
                beneficiary_ids.append(id_item.text())
                lastname = ln_item.text() if ln_item else ""
                firstname = fn_item.text() if fn_item else ""
                beneficiary_names.append(f"{lastname}, {firstname}")

        # Show interactive confirmation dialogue listing the items to move
        confirm_msg = (
            f"Are you sure you want to relocate the following {len(beneficiary_ids)} beneficiary(ies) to:\n"
            f"👉 <b>{target_site_name}</b>?\n\n" +
            "\n".join(f"• {name} (ID: {bid})" for name, bid in zip(beneficiary_names[:10], beneficiary_ids[:10]))
        )
        if len(beneficiary_ids) > 10:
            confirm_msg += f"\n... and {len(beneficiary_ids) - 10} more."

        reply = QMessageBox.question(
            self, "Confirm Bulk Relocation", confirm_msg,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            from core.database import bulk_transfer_beneficiaries
            success, err = bulk_transfer_beneficiaries(beneficiary_ids, target_site_id)
            if success:
                QMessageBox.information(
                    self, "Success",
                    f"Successfully relocated {len(beneficiary_ids)} beneficiary(ies) to {target_site_name}."
                )
                # Refresh table by reloading beneficiaries for current source site
                source_site_id = self.cmb_source.currentData()
                self.load_beneficiaries(source_site_id)
            else:
                QMessageBox.critical(
                    self, "Transfer Failed",
                    f"Failed to execute bulk transfer:\n{err}"
                )
