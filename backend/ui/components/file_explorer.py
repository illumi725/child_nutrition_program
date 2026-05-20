from PySide6.QtWidgets import QTreeView, QFileSystemModel
from PySide6.QtCore import QDir, Signal, Qt, QModelIndex
import os

class CheckableFileSystemModel(QFileSystemModel):
    checked_files_changed = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.checked_paths = set()

    def flags(self, index: QModelIndex):
        default_flags = super().flags(index)
        if index.column() == 0:
            return default_flags | Qt.ItemIsUserCheckable
        return default_flags

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if role == Qt.DecorationRole and index.column() == 0:
            from ui.theme import create_emoji_icon
            if self.isDir(index):
                return create_emoji_icon("📁", 24)
            else:
                return create_emoji_icon("📄", 24)
        
        if role == Qt.CheckStateRole and index.column() == 0:
            path = self.filePath(index)
            if path in self.checked_paths:
                return Qt.Checked
            return Qt.Unchecked
        return super().data(index, role)

    def setData(self, index: QModelIndex, value: int, role: int = Qt.EditRole) -> bool:
        if role == Qt.CheckStateRole and index.column() == 0:
            path = self.filePath(index)
            is_checked = (value == Qt.Checked.value)
            
            self._set_checked_recursive(path, is_checked)
            
            # Force UI to redraw checkboxes
            self.layoutChanged.emit()
            self.checked_files_changed.emit(self.get_all_checked_xlsx())
            return True
            
        return super().setData(index, value, role)

    def _set_checked_recursive(self, path, is_checked):
        if is_checked:
            self.checked_paths.add(path)
        else:
            self.checked_paths.discard(path)
            # Uncheck all ancestor directories so parent folders visually uncheck
            parent = os.path.dirname(path)
            while parent and parent != os.path.dirname(parent):
                if parent in self.checked_paths:
                    self.checked_paths.discard(parent)
                parent = os.path.dirname(parent)
            
        if os.path.isdir(path):
            try:
                for item in os.listdir(path):
                    child_path = os.path.join(path, item)
                    if item.startswith('.') or item.startswith('~'):
                        continue
                    if os.path.isdir(child_path) or child_path.endswith('.xlsx'):
                        self._set_checked_recursive(child_path, is_checked)
            except PermissionError:
                pass

    def get_all_checked_xlsx(self):
        return [p for p in self.checked_paths if p.endswith('.xlsx') and os.path.isfile(p)]


class FileExplorer(QTreeView):
    files_selected = Signal(list)

    def __init__(self, root_path):
        super().__init__()
        self.model = CheckableFileSystemModel()
        self.model.setRootPath(root_path)
        # Filter to only show directories and xlsx files
        self.model.setNameFilters(["*.xlsx"])
        self.model.setNameFilterDisables(False)
        
        self.setModel(self.model)
        self.setRootIndex(self.model.index(root_path))
        
        # We don't need row selection anymore since we use checkboxes
        self.setSelectionMode(QTreeView.NoSelection)
        self.setAnimated(True)
        self.setIndentation(20)
        self.setSortingEnabled(True)

        # Hide extra columns (size, type, date modified) for a cleaner look
        self.setColumnHidden(1, True)
        self.setColumnHidden(2, True)
        self.setColumnHidden(3, True)

        self.model.checked_files_changed.connect(self.files_selected.emit)

    def set_root_path(self, path):
        self.model.setRootPath(path)
        self.setRootIndex(self.model.index(path))
