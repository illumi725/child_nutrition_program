from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QComboBox,
    QPushButton,
    QFormLayout,
)


class EditBeneficiaryDialog(QDialog):
    def __init__(self, record_data, sites, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Beneficiary Before Registering")
        self.setMinimumWidth(400)

        self.record_data = record_data
        self.sites = sites

        self.setup_ui()
        self.populate_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        form_layout = QFormLayout()

        self.txt_lastname = QLineEdit()
        self.txt_firstname = QLineEdit()
        self.txt_middlename = QLineEdit()
        self.txt_birthday = QLineEdit()
        self.txt_birthday.setPlaceholderText("YYYY-MM-DD")

        self.cmb_gender = QComboBox()
        self.cmb_gender.addItems(["Boy", "Girl"])

        self.txt_weight = QLineEdit()
        self.txt_height = QLineEdit()
        self.txt_date_collected = QLineEdit()
        self.txt_date_collected.setPlaceholderText("YYYY-MM-DD")

        self.cmb_site = QComboBox()
        for s in self.sites:
            batch_str = f" - Batch {s['batch']}" if s.get("batch") else ""
            self.cmb_site.addItem(
                f"{s['site_name']} ({s['barangay_name']}){batch_str}",
                userData=s["site_id"],
            )

        form_layout.addRow("Last Name:", self.txt_lastname)
        form_layout.addRow("First Name:", self.txt_firstname)
        form_layout.addRow("Middle Name:", self.txt_middlename)
        form_layout.addRow("Birthday:", self.txt_birthday)
        form_layout.addRow("Gender:", self.cmb_gender)
        form_layout.addRow("Weight (kg):", self.txt_weight)
        form_layout.addRow("Height (cm):", self.txt_height)
        form_layout.addRow("Date Collected:", self.txt_date_collected)
        form_layout.addRow("Feeding Site:", self.cmb_site)

        layout.addLayout(form_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Confirm and Register")

        self.btn_save.clicked.connect(self.accept)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)

        layout.addLayout(btn_layout)

    def populate_data(self):
        self.txt_lastname.setText(self.record_data.get("lastname", ""))
        self.txt_firstname.setText(self.record_data.get("firstname", ""))
        self.txt_middlename.setText(self.record_data.get("middlename", ""))
        self.txt_birthday.setText(self.record_data.get("birthday", ""))

        gender = self.record_data.get("gender", "Boy").capitalize()
        idx = self.cmb_gender.findText(gender)
        if idx >= 0:
            self.cmb_gender.setCurrentIndex(idx)

        self.txt_weight.setText(str(self.record_data.get("weight", "")))
        self.txt_height.setText(str(self.record_data.get("height", "")))
        self.txt_date_collected.setText(str(self.record_data.get("date_collected", "")))

        suggested_site_id = self.record_data.get("suggested_site_id")
        if suggested_site_id:
            for i in range(self.cmb_site.count()):
                if self.cmb_site.itemData(i) == suggested_site_id:
                    self.cmb_site.setCurrentIndex(i)
                    break

    def get_data(self):
        return {
            "lastname": self.txt_lastname.text().strip(),
            "firstname": self.txt_firstname.text().strip(),
            "middlename": self.txt_middlename.text().strip(),
            "birthday": self.txt_birthday.text().strip(),
            "gender": self.cmb_gender.currentText(),
            "weight": float(self.txt_weight.text().strip())
            if self.txt_weight.text().strip()
            else None,
            "height": float(self.txt_height.text().strip())
            if self.txt_height.text().strip()
            else None,
            "date_collected": self.txt_date_collected.text().strip(),
            "site_id": self.cmb_site.currentData(),
        }
