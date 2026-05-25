from PySide6.QtGui import QPalette, QColor, QFont, QIcon, QPixmap, QPainter
from PySide6.QtWidgets import QApplication, QProxyStyle, QStyle
from PySide6.QtCore import Qt


def create_emoji_icon(emoji_char, size=48):
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    font = painter.font()
    # Emphasize Apple Color Emoji if available, or just generic sans-serif which resolves emojis  # noqa: E501
    font.setFamily("Apple Color Emoji")
    font.setPixelSize(int(size * 0.75))
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignCenter, emoji_char)
    painter.end()
    return QIcon(pixmap)


class EmojiProxyStyle(QProxyStyle):
    def standardIcon(self, standardIcon, option=None, widget=None):
        if standardIcon == QStyle.SP_MessageBoxInformation:
            return create_emoji_icon("ℹ️")
        elif standardIcon == QStyle.SP_MessageBoxWarning:
            return create_emoji_icon("⚠️")
        elif standardIcon == QStyle.SP_MessageBoxCritical:
            return create_emoji_icon("❌")
        elif standardIcon == QStyle.SP_MessageBoxQuestion:
            return create_emoji_icon("❓")
        elif standardIcon == QStyle.SP_DirIcon:
            return create_emoji_icon("📁", 24)
        elif standardIcon == QStyle.SP_FileIcon:
            return create_emoji_icon("📄", 24)
        elif standardIcon == QStyle.SP_DirHomeIcon:
            return create_emoji_icon("🏠", 24)
        elif standardIcon == QStyle.SP_DialogOkButton:
            return create_emoji_icon("✅", 20)
        elif standardIcon == QStyle.SP_DialogCancelButton:
            return create_emoji_icon("❌", 20)
        elif standardIcon == QStyle.SP_DialogCloseButton:
            return create_emoji_icon("✖️", 20)
        elif standardIcon == QStyle.SP_DialogYesButton:
            return create_emoji_icon("👍", 20)
        elif standardIcon == QStyle.SP_DialogNoButton:
            return create_emoji_icon("👎", 20)
        elif standardIcon == QStyle.SP_DialogSaveButton:
            return create_emoji_icon("💾", 20)
        elif standardIcon == QStyle.SP_DialogOpenButton:
            return create_emoji_icon("📂", 20)
        elif standardIcon == QStyle.SP_DialogHelpButton:
            return create_emoji_icon("❓", 20)
        return super().standardIcon(standardIcon, option, widget)


def apply_theme(app: QApplication, mode: str):
    """
    Applies a macOS-inspired global QPalette and stylesheet for the application.
    mode should be 'light' or 'dark'.
    """
    app.setStyle(EmojiProxyStyle(app.style().name()))

    palette = QPalette()

    # Base Fonts (macOS-like)
    font = QFont("San Francisco", 10)
    font.setStyleHint(QFont.SansSerif)
    app.setFont(font)

    is_dark = mode == "dark"

    # Colors
    if is_dark:
        bg_color = QColor(30, 30, 30)
        window_color = QColor(40, 40, 40)
        text_color = QColor(240, 240, 240)
        text_disabled = QColor(120, 120, 120)
        base_color = QColor(45, 45, 45)
        alt_base_color = QColor(55, 55, 55)
        primary_blue = QColor(10, 132, 255)  # macOS dark primary
        highlight_color = primary_blue
        highlight_text = QColor(255, 255, 255)
    else:
        bg_color = QColor(236, 236, 236)
        window_color = QColor(245, 245, 245)
        text_color = QColor(20, 20, 20)
        text_disabled = QColor(160, 160, 160)
        base_color = QColor(255, 255, 255)
        alt_base_color = QColor(246, 246, 246)
        primary_blue = QColor(0, 122, 255)  # macOS light primary
        highlight_color = primary_blue
        highlight_text = QColor(255, 255, 255)

    # Set Palette Roles
    palette.setColor(QPalette.Window, window_color)
    palette.setColor(QPalette.WindowText, text_color)
    palette.setColor(QPalette.Base, base_color)
    palette.setColor(QPalette.AlternateBase, alt_base_color)
    palette.setColor(QPalette.ToolTipBase, base_color)
    palette.setColor(QPalette.ToolTipText, text_color)
    palette.setColor(QPalette.Text, text_color)
    palette.setColor(QPalette.Button, bg_color)
    palette.setColor(QPalette.ButtonText, text_color)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, primary_blue)
    palette.setColor(QPalette.Highlight, highlight_color)
    palette.setColor(QPalette.HighlightedText, highlight_text)

    # Disabled text
    palette.setColor(QPalette.Disabled, QPalette.Text, text_disabled)
    palette.setColor(QPalette.Disabled, QPalette.WindowText, text_disabled)
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, text_disabled)

    app.setPalette(palette)

    # Inform Qt of the current color scheme so native icons (QMessageBox, folders) match the theme correctly  # noqa: E501
    if hasattr(app.styleHints(), "setColorScheme"):
        app.styleHints().setColorScheme(
            Qt.ColorScheme.Dark if is_dark else Qt.ColorScheme.Light
        )

    # Global Stylesheet for fixing complex widget bugs and standardizing macOS shapes
    border_color = "#3a3a3a" if is_dark else "#d1d1d1"
    btn_bg = "#3a3a3a" if is_dark else "#ffffff"
    btn_hover = "#4a4a4a" if is_dark else "#f0f0f0"
    btn_pressed = "#2a2a2a" if is_dark else "#e0e0e0"

    combo_bg = "#3a3a3a" if is_dark else "#ffffff"
    combo_text = "#ffffff" if is_dark else "#000000"
    combo_sel_bg = primary_blue.name()

    chk_border = "#777777" if is_dark else "#a0a0a0"
    chk_bg = "#1a1a1a" if is_dark else "#ffffff"

    global_qss = f"""
    QWidget {{
        font-family: "San Francisco", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }}
    
    QLineEdit, QSpinBox, QDateEdit {{
        border: 1px solid {border_color};
        border-radius: 5px;
        padding: 5px;
        background-color: {base_color.name()};
        color: {text_color.name()};
    }}
    QLineEdit:focus, QSpinBox:focus, QDateEdit:focus {{
        border: 2px solid {primary_blue.name()};
    }}
    
    QPushButton {{
        background-color: {btn_bg};
        border: 1px solid {border_color};
        border-radius: 5px;
        padding: 6px 14px;
        color: {text_color.name()};
        font-weight: 500;
    }}
    QPushButton:hover {{
        background-color: {btn_hover};
    }}
    QPushButton:pressed {{
        background-color: {btn_pressed};
    }}
    QPushButton:disabled {{
        color: {text_disabled.name()};
        background-color: transparent;
        border: 1px solid {border_color};
    }}
    
    QComboBox {{
        border: 1px solid {border_color};
        border-radius: 5px;
        padding: 5px;
        background-color: {base_color.name()};
        color: {text_color.name()};
    }}
    QComboBox:focus {{
        border: 2px solid {primary_blue.name()};
    }}
    QComboBox QAbstractItemView {{
        background-color: {combo_bg};
        color: {combo_text};
        selection-background-color: {combo_sel_bg};
        selection-color: white;
        border: 1px solid {border_color};
    }}
    
    QCheckBox {{
        color: {text_color.name()};
        spacing: 5px;
    }}
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border: 1px solid {chk_border};
        background-color: {chk_bg};
        border-radius: 4px;
    }}
    QCheckBox::indicator:checked {{
        background-color: {primary_blue.name()};
        border: 1px solid {primary_blue.name()};
        image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='white'><path d='M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z'/></svg>");
    }}
    
    QTableWidget {{
        border: 1px solid {border_color};
        border-radius: 5px;
        background-color: {base_color.name()};
        alternate-background-color: {alt_base_color.name()};
        color: {text_color.name()};
        gridline-color: {border_color};
    }}
    QHeaderView::section {{
        background-color: {window_color.name()};
        color: {text_color.name()};
        padding: 4px;
        border: 1px solid {border_color};
        font-weight: bold;
    }}
    
    QGroupBox {{
        font-weight: bold;
        border: 1px solid {border_color};
        border-radius: 6px;
        margin-top: 10px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top center;
        padding: 0 5px;
        color: {text_color.name()};
    }}
    
    /* Scrollbars */
    QScrollBar:vertical {{
        border: none;
        background: transparent;
        width: 10px;
        margin: 0px 0px 0px 0px;
    }}
    QScrollBar::handle:vertical {{
        background: {border_color};
        min-height: 20px;
        border-radius: 4px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    """  # noqa: E501

    app.setStyleSheet(global_qss)
