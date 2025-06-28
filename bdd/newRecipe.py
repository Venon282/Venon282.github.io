import sys
import sqlite3
import json
from PyQt6.QtWidgets import (QApplication, QMainWindow, QLabel, QLineEdit, QPushButton,
                             QVBoxLayout, QWidget, QStatusBar, QMessageBox, QSplitter,
                             QComboBox, QHBoxLayout, QFormLayout, QGroupBox, QTextEdit,
                             QDateTimeEdit, QFileDialog, QSpinBox,
                             QListView)
from PyQt6.QtCore import Qt, QDateTime, QStringListModel

class UI:
    def __init__(self, main_window, title, width, height):
        # Initialize the main window
        self.main_window = main_window
        self.main_window.setWindowTitle(title)
        self.main_window.resize(width, height)

        self._central()

    def get_section(self, title):
        section = QGroupBox(title)
        section.setStyleSheet(
            "QGroupBox {"
            "border: 2px solid #3A3A3A;"
            "border-radius: 5px;"
            "margin-top: 10px;"
            "}"
            "QGroupBox::title {"
            "subcontrol-origin: margin;"
            "subcontrol-position: top center;"
            "padding: 0 3px;"
            "}"
        )
        return section

    def get_interactive_list(self):
        def addItem():
            text = edit.text().strip()
            if not text:
                QMessageBox.warning(self.main_window, "Warning", "Please enter text to add.")
                return

            items = model.stringList()
            items.append(text)
            model.setStringList(items)
            edit.clear()

        def deleteItem():
            indexes = view.selectedIndexes()
            if not indexes:
                QMessageBox.warning(self.main_window, "Warning", "Please select an item to delete.")
                return
            row = indexes[0].row()
            items = model.stringList()
            items.pop(row)
            model.setStringList(items)

        # Initialize list data and model
        model = QStringListModel()

        # Setup UI
        view = QListView()
        view.setModel(model)

        # Elements
        edit = QLineEdit()
        add_button = QPushButton('Add Item')
        delete_button = QPushButton('Delete Selected')

        # Behavior
        add_button.clicked.connect(addItem)
        delete_button.clicked.connect(deleteItem)

        return view, edit, add_button, delete_button

    def _central(self):
        # Central widget
        central = QWidget()
        layout = QHBoxLayout()
        central.setLayout(layout)
        self.main_window.setCentralWidget(central)

        # add childs
        self._recipe_details(layout)
        self._recipe(layout)

    def _recipe_details(self, parent):
        self.recipe_dtls_layout = QFormLayout()

        # name
        self.name = QLineEdit()
        self.recipe_dtls_layout.addRow(QLabel("Name:"), self.name)

        # rate
        self.rate = QComboBox()
        self.rate.addItems([''] + list(map(str, range(0, 11))))
        self.recipe_dtls_layout.addRow(QLabel('Rate:'), self.rate)

        # description
        self.description = QTextEdit()
        self.recipe_dtls_layout.addRow(QLabel('Description:'), self.description)

        # create at
        self.created_at = QDateTimeEdit()
        self.created_at.setDisplayFormat('dd-MM-yyyy HH:mm:ss')
        self.created_at.setDateTime(QDateTime.currentDateTime())
        self.created_at.setReadOnly(True)
        self.recipe_dtls_layout.addRow(QLabel('Created at:'), self.created_at)

        # update at
        self.updated_at = QDateTimeEdit()
        self.updated_at.setDisplayFormat('dd-MM-yyyy HH:mm:ss')
        self.updated_at.setDateTime(QDateTime.currentDateTime())
        self.updated_at.setReadOnly(True)
        self.recipe_dtls_layout.addRow(QLabel('Updated at:'), self.updated_at)

        section = self.get_section('Recipe Details')
        section.setLayout(self.recipe_dtls_layout)
        parent.addWidget(section)

    def _recipe(self, parent):
        self.recipe_layout = QFormLayout()

        self.file_button = QPushButton('search...')
        self.file_button.clicked.connect(self.main_window.fill_form_with_json_recipe)
        self.recipe_layout.addRow(QLabel('Recipe JSON file'), self.file_button)

        self.nb_peoples = QSpinBox()
        self.nb_peoples.setSuffix('   peoples.')
        self.nb_peoples.setMinimum(1)
        self.nb_peoples.setValue(4)
        self.recipe_layout.addRow(QLabel('For '), self.nb_peoples)

        self.recipe_layout.addRow(QLabel())
        self.recipe_layout.addRow(QLabel('Ingredients:'))
        self.ingrdts_view, self.ingrdts_edit, self.ingrdts_add, self.ingrdts_delete = self.get_interactive_list()
        self.ingrdts_edit.setPlaceholderText('Entre your ingredient...')
        self.recipe_layout.addRow(self.ingrdts_view)
        self.recipe_layout.addRow(self.ingrdts_edit)
        self.recipe_layout.addRow(self.ingrdts_add)
        self.recipe_layout.addRow(self.ingrdts_delete)

        self.recipe_layout.addRow(QLabel())
        self.recipe_layout.addRow(QLabel('Steps:'))
        self.steps_view, self.steps_edit, self.steps_add, self.steps_delete = self.get_interactive_list()
        self.steps_edit.setPlaceholderText('Entre your steps...')
        self.recipe_layout.addRow(self.steps_view)
        self.recipe_layout.addRow(self.steps_edit)
        self.recipe_layout.addRow(self.steps_add)
        self.recipe_layout.addRow(self.steps_delete)

        section = self.get_section('Recipe')
        section.setLayout(self.recipe_layout)
        parent.addWidget(section)

class NewRecipe(QMainWindow):
    def __init__(self, db_path='./recipe.db', width=800, height=600, title='New Recipe', **kwargs):
        super().__init__()

        # parameters
        self.db_path = db_path
        self.conn = None

        # Build the structure
        self.ui = UI(self, title, width, height)

        self._status()
        self.load_database(path=self.db_path)

    def _status(self):
        # Status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)

    def load_database(self, path):
        try:
            if self.conn:
                self.conn.close()
            self.conn = sqlite3.connect(path)
            self.status.showMessage(f"Opened {path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open database: {e}")

    def fill_form_with_json_recipe(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select recipe JSON", "", "JSON Files (*.json *.JSON)")
        if path:
            with open(path, 'r', encoding='utf-8-sig') as file:
                recipe = json.load(file)

            if 'nb_peoples' in recipe and isinstance(recipe['nb_peoples'], int) and recipe['nb_peoples'] > 0 and recipe['nb_peoples'] < 100:
                self.ui.nb_peoples.setValue(recipe['nb_peoples'])

            for key in ['ingredients', 'steps']:
                elements = recipe.get(key)

                if not isinstance(elements, list):
                    continue

                # choose the right QListView
                if key == 'ingredients':
                    view = self.ui.ingrdts_view
                else:
                    view = self.ui.steps_view

                model = view.model()                     # type: QStringListModel
                items = model.stringList()               # current items
                items.extend(str(el) for el in elements) # append each new element
                model.setStringList(items)               # push back to the view



if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = NewRecipe()
    window.show()
    sys.exit(app.exec())
