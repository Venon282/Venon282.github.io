from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QToolButton, QMenu, QLabel, QWidgetAction,
    QHBoxLayout, QStyle, QSizePolicy, QScrollArea, QCheckBox, QRadioButton,
    QLineEdit
)
from PyQt6.QtGui import QAction, QIcon, QFontMetrics
from PyQt6.QtCore import Qt, QTimer, QPoint, pyqtSignal
import sys



class CheckComboBox(QWidget):
    """
    Widget simulant un QComboBox à sélection multiple ou simple.
    """
    selectionChanged = pyqtSignal(list)

    def __init__(
        self,
        placeholder="Sélectionnez...",
        maxVisibleItems=8,
        multiSelect=True,
        parent=None
    ):
        super().__init__(parent)
        self._items = []          # list of (label, value, tooltip)
        self._buttons = []        # QCheckBox or QRadioButton
        self.maxVisibleItems = maxVisibleItems
        self.multiSelect = multiSelect

        # Bouton principal stylisé comme QComboBox
        self.button = QToolButton(self)
        self.button.setText(placeholder)
        self.button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.button.setStyleSheet(
            "QToolButton { text-align: left; padding: 4px;"
            " border: 1px solid gray; border-radius: 4px; }"
        )

        # Menu principal
        self.menu = QMenu(self)
        self.menu.setStyleSheet("QMenu { menu-scrollable: 1; }")
        self.button.setMenu(self.menu)
        self.menu.aboutToShow.connect(self._syncMenuWidth)

        # Zone scrollable pour les boutons
        self.container = QWidget()
        self.vbox = QVBoxLayout(self.container)
        self.vbox.setContentsMargins(0, 0, 0, 0)
        self.vbox.setSpacing(0)

        # -- Add search field above the list --
        self.search_field = QLineEdit(self)
        self.search_field.setPlaceholderText("Search…")
        self.search_field.textChanged.connect(self._filterItems)
        search_action = QWidgetAction(self.menu)
        search_action.setDefaultWidget(self.search_field)
        self.menu.addAction(search_action)                 # put it at the top of the layout


        self.scroll = QScrollArea()
        self.scroll.setWidget(self.container)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._updateScrollHeight()

        # Intégration dans le menu via QWidgetAction
        scroll_action = QWidgetAction(self.menu)
        scroll_action.setDefaultWidget(self.scroll)
        self.menu.addAction(scroll_action)

        self.menu.aboutToShow.connect(self.search_field.setFocus)

        # Layout principal
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.button)

    def _syncMenuWidth(self):
        width = self.button.width()
        self.menu.setMinimumWidth(width)
        self.scroll.setMinimumWidth(width)

    def addItem(self, label: str, value=None, tooltip: str = None):
        """
        Ajoute un item.
        - label: texte affiché
        - value: valeur retournée (par défaut = label)
        - tooltip: texte affiché au survol (optionnel)
        """
        if value is None:
            value = label

        # Choix du widget selon multiSelect
        if self.multiSelect:
            btn = QCheckBox(label)
        else:
            btn = QRadioButton(label)
            btn.setAutoExclusive(False)
        btn.setStyleSheet(type(btn).__name__ + " { padding: 4px; }")
        if tooltip:
            btn.setToolTip(tooltip)
        btn.toggled.connect(lambda checked, b=btn: self._onToggled(b, checked))

        self.vbox.addWidget(btn)
        self._items.append((label, value, tooltip))
        self._buttons.append(btn)
        self._updateScrollHeight()

    def _filterItems(self, text: str):
        """Show only the buttons whose label contains the search text."""
        text = text.lower()
        for btn in self._buttons:
            btn.setVisible(text in btn.text().lower())
        self._updateScrollHeight()    # adjust scroll area if nécessaire

    def addItems(self, items):
        for it in items:
            if isinstance(it, str):
                self.addItem(it)
            elif len(it) == 2:
                self.addItem(it[0], it[1])
            elif len(it) == 3:
                self.addItem(it[0], it[1], it[2])
            else:
                raise ValueError("Items must be str or tuple(label, value[, tooltip])")

    def _updateScrollHeight(self):
        if not self._buttons:
            return
        fm = self.container.fontMetrics()
        item_h = fm.height() + 8
        self.scroll.setMaximumHeight(item_h * self.maxVisibleItems)

    def _onToggled(self, btn, checked):
        # Sélection simple : décocher les autres
        if not self.multiSelect and checked:
            for b in self._buttons:
                if b is not btn:
                    b.blockSignals(True)
                    b.setChecked(False)
                    b.blockSignals(False)
            # fermer le menu
            self.menu.hide()
        self._updateDisplay()
        self.search_field.setFocus()

    def _updateDisplay(self):
        labels = []
        values = []
        for (label, value, _), btn in zip(self._items, self._buttons):
            if btn.isChecked():
                labels.append(label)
                values.append(value)

        text = ", ".join(labels) if labels else "Sélectionnez..."
        fm = self.button.fontMetrics()
        avail = max(10, self.button.width() - 20)
        self.button.setText(fm.elidedText(text, Qt.TextElideMode.ElideRight, avail))
        self.selectionChanged.emit(values)

    def selectedValues(self):
        return [v for (_, v, _), b in zip(self._items, self._buttons) if b.isChecked()]

    def setSelectedValues(self, values):
        for (_, v, _), b in zip(self._items, self._buttons):
            b.setChecked(v in values)
        self._updateDisplay()

    def clearSelection(self):
        for b in self._buttons:
            b.setChecked(False)
        self._updateDisplay()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._updateDisplay()

# Exemple d'utilisation
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QWidget()
    layout = QHBoxLayout(window)

    combo_multi = CheckComboBox("Multi…", maxVisibleItems=5, multiSelect=True)
    combo_multi.addItems(["A", "B", "C"])
    combo_multi.selectionChanged.connect(lambda v: print("Multi sélection :", v))

    combo_single = CheckComboBox("Single…", maxVisibleItems=5, multiSelect=False)
    combo_single.addItems(["X", "Y", "Z"])
    combo_single.selectionChanged.connect(lambda v: print("Single sélection :", v))

    layout.addWidget(combo_multi)
    layout.addWidget(combo_single)
    window.resize(400, 100)
    window.show()
    sys.exit(app.exec())
