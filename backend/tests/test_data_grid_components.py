from ui.components.data_grid import (
    ActionWidget,
    BirthdayActionWidget,
    NameActionWidget,
    MissingDbActionWidget,
    MissingExcelActionWidget,
    ManageDupWidget,
    ResultsDataGrid,
)


def test_action_widget_emits_and_shows_synced(qapp):
    record = {"baseline_mismatch": True}
    received = {}

    w = ActionWidget(record)

    def on_sync(rec, widget):
        received["rec"] = rec
        received["widget"] = widget

    w.sync_clicked.connect(on_sync)
    # simulate click
    w.btn_sync.click()

    assert "rec" in received and isinstance(received["rec"], dict)
    assert received["rec"].get("baseline_mismatch") is True

    # mark as synced should update UI only
    w.mark_as_synced()
    assert not w.btn_sync.isEnabled()
    assert w.btn_sync.text() == "Synced ✓"


def test_birthday_widget_actions_and_resolved(qapp):
    record = {"birthday_mismatch": True}
    received = []

    w = BirthdayActionWidget(record)
    w.action_clicked.connect(
        lambda action, rec, widget: received.append((action, rec, widget))
    )

    w.btn_excel.click()
    w.btn_db.click()
    w.btn_manual.click()

    assert len(received) == 3
    assert received[0][0] == "use_excel"
    assert received[1][0] == "use_db"
    assert received[2][0] == "manual"

    w.mark_as_resolved()
    # after resolved, action buttons are hidden
    assert not w.btn_excel.isVisible()


def test_name_widget_actions_and_resolved(qapp):
    record = {"name_mismatch": True}
    received = []

    w = NameActionWidget(record)
    w.action_clicked.connect(
        lambda action, rec, widget: received.append((action, rec, widget))
    )

    w.btn_excel.click()
    w.btn_db.click()
    w.btn_manual.click()

    assert len(received) == 3
    assert received[0][0] == "use_excel"

    w.mark_as_resolved()
    assert not w.btn_manual.isVisible()


def test_missing_db_widget_and_resolved(qapp):
    record = {"_added_to_db": False}
    received = []

    w = MissingDbActionWidget(record)
    w.action_clicked.connect(
        lambda action, rec, widget: received.append((action, rec, widget))
    )

    w.btn_add.click()
    assert received and received[0][0] == "add_to_db"

    w.mark_as_resolved()
    assert not w.btn_add.isVisible()


def test_missing_excel_widget_and_resolved(qapp):
    record = {"_deleted_from_db": False}
    received = []

    w = MissingExcelActionWidget(record)
    w.action_clicked.connect(
        lambda action, rec, widget: received.append((action, rec, widget))
    )

    w.btn_delete.click()
    assert received and received[0][0] == "delete_from_db"

    w.mark_as_resolved()
    assert not w.btn_delete.isVisible()


def test_manage_dup_widget_emits_manage(qapp):
    record = {}
    received = []

    w = ManageDupWidget(record)
    w.action_clicked.connect(
        lambda action, rec, widget: received.append((action, rec, widget))
    )

    # find the child button and click
    btn = w.findChild(type(w.layout().itemAt(0).widget()))
    # simpler: trigger the signal by calling clicked on first child
    btn = w.layout().itemAt(0).widget()
    btn.click()

    assert received and received[0][0] == "manage"


def test_results_data_grid_action_emits(qapp):
    grid = ResultsDataGrid()
    received = []

    # define columns and a single record with birthday action
    columns = [{"label": "Name", "key": "excel.raw_name"}]
    record = {
        "excel": {"raw_name": "Test", "birthday": "2000-01-02"},
        "db": {"firstname": "T", "lastname": "S"},
    }

    def on_action(action, rec, widget):
        received.append((action, rec, widget))

    grid.action_triggered.connect(on_action)
    grid.set_data([record], columns, action_label="BirthdayActions")

    # get cell widget and click the excel button
    cell = grid.cellWidget(0, 0)
    assert cell is not None
    cell.btn_excel.click()

    assert received and received[0][0] == "use_excel"


if __name__ == "__main__":
    test_action_widget_emits_and_shows_synced()
    test_birthday_widget_actions_and_resolved()
    test_name_widget_actions_and_resolved()
    test_missing_db_widget_and_resolved()
    test_missing_excel_widget_and_resolved()
    test_manage_dup_widget_emits_manage()
    test_results_data_grid_action_emits()
    print("OK")
