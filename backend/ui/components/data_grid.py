from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QWidget, QHBoxLayout, QPushButton, QAbstractItemView
from PySide6.QtCore import Qt, Signal

class ActionWidget(QWidget):
    sync_clicked = Signal(dict, QWidget)
    
    def __init__(self, record_data, default_label="Sync"):
        super().__init__()
        self.record_data = record_data
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        
        self.btn_sync = QPushButton(default_label)
        
        # If it's a match and there's no mismatch, disable the button
        if 'baseline_mismatch' in record_data and not record_data['baseline_mismatch']:
            self.mark_as_synced()
        else:
            self.btn_sync.clicked.connect(self._on_sync)
            
        layout.addWidget(self.btn_sync)

    def mark_as_synced(self):
        self.record_data['baseline_mismatch'] = False
        self.btn_sync.setEnabled(False)
        self.btn_sync.setText("Synced ✓")
        self.btn_sync.setStyleSheet("color: #27ae60; font-weight: bold; background: transparent; border: none;")

    def _on_sync(self):
        self.sync_clicked.emit(self.record_data, self)

class BirthdayActionWidget(QWidget):
    action_clicked = Signal(str, dict, QWidget) # action_name (use_excel, use_db, manual), record_data, widget
    
    def __init__(self, record_data):
        super().__init__()
        self.record_data = record_data
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(5)
        
        self.btn_excel = QPushButton("Use Excel")
        self.btn_db = QPushButton("Use DB")
        self.btn_manual = QPushButton("Manual")
        
        self.btn_excel.setStyleSheet("background-color: #2980b9; color: white;")
        self.btn_db.setStyleSheet("background-color: #8e44ad; color: white;")
        self.btn_manual.setStyleSheet("background-color: #f39c12; color: white;")
        
        self.btn_excel.clicked.connect(lambda: self.action_clicked.emit("use_excel", self.record_data, self))
        self.btn_db.clicked.connect(lambda: self.action_clicked.emit("use_db", self.record_data, self))
        self.btn_manual.clicked.connect(lambda: self.action_clicked.emit("manual", self.record_data, self))
        
        layout.addWidget(self.btn_excel)
        layout.addWidget(self.btn_db)
        layout.addWidget(self.btn_manual)
        
        if 'birthday_mismatch' in record_data and not record_data['birthday_mismatch']:
            self.mark_as_resolved()

    def mark_as_resolved(self):
        self.btn_excel.setVisible(False)
        self.btn_db.setVisible(False)
        self.btn_manual.setVisible(False)
        
        lbl = QPushButton("Resolved ✓")
        lbl.setEnabled(False)
        lbl.setStyleSheet("color: #27ae60; font-weight: bold; background: transparent; border: none;")
        self.layout().addWidget(lbl)

class NameActionWidget(QWidget):
    action_clicked = Signal(str, dict, QWidget)
    
    def __init__(self, record_data):
        super().__init__()
        self.record_data = record_data
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(5)
        
        self.btn_excel = QPushButton("Use Excel")
        self.btn_db = QPushButton("Use DB")
        self.btn_manual = QPushButton("Manual")
        
        self.btn_excel.setStyleSheet("background-color: #2980b9; color: white;")
        self.btn_db.setStyleSheet("background-color: #8e44ad; color: white;")
        self.btn_manual.setStyleSheet("background-color: #f39c12; color: white;")
        
        self.btn_excel.clicked.connect(lambda: self.action_clicked.emit("use_excel", self.record_data, self))
        self.btn_db.clicked.connect(lambda: self.action_clicked.emit("use_db", self.record_data, self))
        self.btn_manual.clicked.connect(lambda: self.action_clicked.emit("manual", self.record_data, self))
        
        layout.addWidget(self.btn_excel)
        layout.addWidget(self.btn_db)
        layout.addWidget(self.btn_manual)
        
        if 'name_mismatch' in record_data and not record_data['name_mismatch']:
            self.mark_as_resolved()

    def mark_as_resolved(self):
        self.btn_excel.setVisible(False)
        self.btn_db.setVisible(False)
        self.btn_manual.setVisible(False)
        
        lbl = QPushButton("Resolved ✓")
        lbl.setEnabled(False)
        lbl.setStyleSheet("color: #27ae60; font-weight: bold; background: transparent; border: none;")
        self.layout().addWidget(lbl)

class MissingDbActionWidget(QWidget):
    action_clicked = Signal(str, dict, QWidget)
    
    def __init__(self, record_data):
        super().__init__()
        self.record_data = record_data
        
        layout = QHBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        self.setLayout(layout)
        
        self.btn_add = QPushButton("Add to DB")
        self.btn_add.setStyleSheet("background-color: #3498db; color: white;")
        self.btn_add.clicked.connect(lambda: self.action_clicked.emit("add_to_db", self.record_data, self))
        
        layout.addWidget(self.btn_add)
        
        if record_data.get('_added_to_db', False):
            self.mark_as_resolved()

    def mark_as_resolved(self):
        self.btn_add.setVisible(False)
        lbl = QPushButton("Added ✓")
        lbl.setEnabled(False)
        lbl.setStyleSheet("color: #27ae60; font-weight: bold; background: transparent; border: none;")
        self.layout().addWidget(lbl)

class ManageDupWidget(QWidget):
    """Action widget for the Excel/DB Duplicates tab — shows a red Manage button."""
    action_clicked = Signal(str, dict, QWidget)

    def __init__(self, record_data):
        super().__init__()
        self.record_data = record_data
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        btn = QPushButton("🛠 Manage")
        btn.setStyleSheet(
            "background-color: #c0392b; color: white; font-weight: bold; padding: 3px 8px; border-radius: 3px;"
        )
        btn.clicked.connect(lambda: self.action_clicked.emit("manage", self.record_data, self))
        layout.addWidget(btn)


class ResultsDataGrid(QTableWidget):
    action_triggered = Signal(str, dict, QWidget) # action_name, record_data, action_widget

    def __init__(self):
        super().__init__()
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(True)
        self.horizontalHeader().setStretchLastSection(True)
        self.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ecf0f1;
                font-size: 12px;
                background-color: white;
                color: #2c3e50;
                alternate-background-color: #f8f9fa;
            }
            QHeaderView::section {
                background-color: #2c3e50;
                color: white;
                padding: 6px;
                font-weight: bold;
                border: none;
            }
            QTableWidget::item:selected {
                background-color: #d6eaf8;
                color: #2c3e50;
            }
        """)

    def set_data(self, results_list, columns, action_label=None):
        self.clear()
        self.setRowCount(len(results_list))
        
        headers = [col['label'] for col in columns]
        if action_label:
            headers.insert(0, "Actions")
            
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)

        for row_idx, record in enumerate(results_list):
            col_offset = 0
            if action_label:
                col_offset = 1
                if action_label == "BirthdayActions":
                    action_widget = BirthdayActionWidget(record)
                    action_widget.action_clicked.connect(lambda action, rec, aw: self.action_triggered.emit(action, rec, aw))
                elif action_label == "NameActions":
                    action_widget = NameActionWidget(record)
                    action_widget.action_clicked.connect(lambda action, rec, aw: self.action_triggered.emit(action, rec, aw))
                elif action_label == "MissingDbActions":
                    action_widget = MissingDbActionWidget(record)
                    action_widget.action_clicked.connect(lambda action, rec, aw: self.action_triggered.emit(action, rec, aw))
                elif action_label == "ManageDup":
                    action_widget = ManageDupWidget(record)
                    action_widget.action_clicked.connect(lambda action, rec, aw: self.action_triggered.emit(action, rec, aw))
                else:
                    action_widget = ActionWidget(record, default_label=action_label)
                    action_widget.sync_clicked.connect(lambda rec, aw, lbl=action_label: self.action_triggered.emit(lbl, rec, aw))

                self.setCellWidget(row_idx, 0, action_widget)

            for col_idx, col in enumerate(columns):
                val = ""
                if 'getter' in col:
                    try:
                        val = col['getter'](record)
                    except:
                        val = ""
                else:
                    # Fetch nested keys like 'excel.lastname'
                    val = record
                    for key in col['key'].split('.'):
                        val = val.get(key, {}) if isinstance(val, dict) else ""
                    if isinstance(val, dict): val = ""
                
                item = QTableWidgetItem(str(val))
                self.setItem(row_idx, col_idx + col_offset, item)

        self.resizeColumnsToContents()
