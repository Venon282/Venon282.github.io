import sys
import sqlite3
import json
from PyQt6.QtWidgets import (QApplication, QMainWindow, QLabel, QLineEdit, QPushButton,
                             QVBoxLayout, QWidget, QStatusBar, QMessageBox, QSplitter,
                             QComboBox, QHBoxLayout, QFormLayout, QGroupBox, QTextEdit,
                             QDateTimeEdit, QFileDialog, QSpinBox, QGridLayout, QScrollArea,
                             QListView, QFrame)
from PyQt6.QtCore import Qt, QDateTime, QByteArray, QStringListModel, QSize, pyqtSignal, QMimeData
from PyQt6.QtGui import QPixmap, QMouseEvent, QCursor, QDrag, QDragEnterEvent, QDragMoveEvent, QDropEvent
from CheckComboBox import CheckComboBox
from pathlib import Path
import json
import shutil

class ThumbnailWidget(QFrame):
    removed = pyqtSignal(int)
    drag_start = pyqtSignal(int)

    def __init__(self, index: int, img_path: str, thumb_size: QSize = QSize(100, 100)):
        super().__init__()
        self.index = index  # on stocke l'index et pas le path
        self.img_path = img_path
        self.thumb_size = thumb_size
        self.setFixedSize(thumb_size)

        self.setStyleSheet("""
            QFrame {
                border: 1px solid #888;
                border-radius: 6px;
                background: #fdfdfd;
            }
            QFrame:hover {
                background: #f5f5f5;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)

        close_btn = QPushButton("×", self)
        close_btn.setFixedSize(18, 18)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: red;
                font-weight: bold;
                border: none;
                font-size: 14px;
            }
        """)
        close_btn.clicked.connect(lambda: self.removed.emit(self.index))

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.addStretch()
        top.addWidget(close_btn)
        layout.addLayout(top)

        pixmap = QPixmap(self.img_path).scaled(
            self.thumb_size - QSize(4, 4), Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        label = QLabel()
        label.setPixmap(pixmap)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label, 1)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            drag = QDrag(self)
            mime = QMimeData()
            mime.setData("application/x-image-index", QByteArray(str(self.index).encode()))
            drag.setMimeData(mime)
            drag.setPixmap(self.grab())
            drag.setHotSpot(event.pos())
            drag.exec(Qt.DropAction.MoveAction)
            self.drag_start.emit(self.index)


class DropGridWidget(QWidget):
    reordered = pyqtSignal(int, int)  # from_index, to_index

    def __init__(self, thumb_size: QSize, spacing: int):
        super().__init__()
        self.thumb_size = thumb_size
        self.spacing = spacing
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasFormat("application/x-image-index"):
            event.acceptProposedAction()

    def dragMoveEvent(self, event: QDragMoveEvent):
        event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        if not event.mimeData().hasFormat("application/x-image-index"):
            return

        from_index = int(bytes(event.mimeData().data("application/x-image-index")).decode())
        pos = event.position().toPoint()

        thumb_w = self.thumb_size.width()
        thumb_h = self.thumb_size.height()
        spacing = self.spacing
        cols = max(1, self.width() // (thumb_w + spacing))

        col = pos.x() // (thumb_w + spacing)
        row = pos.y() // (thumb_h + spacing)
        col = min(col, cols - 1)

        to_index = row * cols + col
        self.reordered.emit(from_index, to_index)
        event.acceptProposedAction()


class ImageSelectorWidget(QWidget):
    """Sélecteur complet avec drag & drop et grid stylée."""
    def __init__(self, thumb_size: QSize = QSize(100, 100)):
        super().__init__()
        self.thumb_size = thumb_size
        self.selected_images: list[str] = []

        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(5)

        btn = QPushButton("Sélectionner des images")
        btn.clicked.connect(self.select_images)
        vbox.addWidget(btn)

        # Scroll & content
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.content = DropGridWidget(self.thumb_size, spacing=4)
        self.content_layout = QGridLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(4)
        self.content.setLayout(self.content_layout)
        self.scroll.setWidget(self.content)
        vbox.addWidget(self.scroll)

        # signal drag & drop
        self.content.reordered.connect(self._reorder_image)

    def select_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Choisir des images", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if files:
            self.selected_images.extend(files)
            self._refresh_grid()

    def _refresh_grid(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        available_width = self.scroll.viewport().width()
        cols = max(1, available_width // (self.thumb_size.width() + self.content_layout.spacing()))

        for idx, path in enumerate(self.selected_images):
            row, col = divmod(idx, cols)
            thumb = ThumbnailWidget(idx, path, self.thumb_size)
            thumb.removed.connect(self._remove_image_by_index)
            self.content_layout.addWidget(thumb, row, col)

    def _remove_image_by_index(self, index: int):
        if 0 <= index < len(self.selected_images):
            self.selected_images.pop(index)
            self._refresh_grid()



    def _remove_image(self, path: str):
        if path in self.selected_images:
            self.selected_images.remove(path)
            self._refresh_grid()

    def _reorder_image(self, from_index: int, to_index: int):
        if from_index < 0 or from_index >= len(self.selected_images):
            return

        img = self.selected_images.pop(from_index)

        if to_index > from_index:
            to_index -= 1

        to_index = max(0, min(to_index, len(self.selected_images)))
        self.selected_images.insert(to_index, img)

        self._refresh_grid()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_grid()

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

        return model, view, edit, add_button, delete_button

    def _central(self):
        # Central widget
        central = QWidget()
        layout = QVBoxLayout()
        info_layout = QHBoxLayout()
        layout.addLayout(info_layout)
        central.setLayout(layout)
        self.main_window.setCentralWidget(central)

        # Submit button
        layout_buttons = QHBoxLayout()
        layout.addLayout(layout_buttons)

        self.submit = QPushButton('Submit')
        self.submit.clicked.connect(self.main_window.submit)
        layout_buttons.addWidget(self.submit)

        self.clean = QPushButton('Clean form')
        self.clean.clicked.connect(self.main_window.clear_all_fields)
        layout_buttons.addWidget(self.clean)


        # add childs
        self._recipe_details(info_layout)
        self._recipe(info_layout)
        self._categories(info_layout)
        self._images(info_layout)


    def _recipe_details(self, parent):
        self.recipe_dtls_layout = QFormLayout()

        # name
        self.name = QLineEdit()
        self.recipe_dtls_layout.addRow(QLabel("Name:"), self.name)

        # time
        self.time = QSpinBox()
        self.time.setMinimum(0)
        self.time.setSuffix('   mn.')
        self.recipe_dtls_layout.addRow(QLabel("Time:"), self.time)

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
        self.ingrdts_model, self.ingrdts_view, self.ingrdts_edit, self.ingrdts_add, self.ingrdts_delete = self.get_interactive_list()
        self.ingrdts_edit.setPlaceholderText('Entre your ingredient...')
        self.recipe_layout.addRow(self.ingrdts_view)
        self.recipe_layout.addRow(self.ingrdts_edit)
        self.recipe_layout.addRow(self.ingrdts_add)
        self.recipe_layout.addRow(self.ingrdts_delete)

        self.recipe_layout.addRow(QLabel())
        self.recipe_layout.addRow(QLabel('Steps:'))
        self.steps_model, self.steps_view, self.steps_edit, self.steps_add, self.steps_delete = self.get_interactive_list()
        self.steps_edit.setPlaceholderText('Entre your steps...')
        self.recipe_layout.addRow(self.steps_view)
        self.recipe_layout.addRow(self.steps_edit)
        self.recipe_layout.addRow(self.steps_add)
        self.recipe_layout.addRow(self.steps_delete)

        section = self.get_section('Recipe')
        section.setLayout(self.recipe_layout)
        parent.addWidget(section)

    def _categories(self, parent):
        self.categories_layout = QFormLayout()

        section = self.get_section('Categories')
        section.setLayout(self.categories_layout)
        parent.addWidget(section)

    def _images(self, parent):
        self.images = ImageSelectorWidget(thumb_size=QSize(100, 100))
        section = self.get_section('Images')
        # section doit être un QWidget avec un layout vide
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.images)
        parent.addWidget(section)

class NewRecipe(QMainWindow):
    def __init__(self, folder_parent='bdd', folder_recipe='recipes', db_path='./recipe.db', width=1300, height=600, title='New Recipe', **kwargs):
        super().__init__()

        if Path(__file__).parent.stem != folder_parent:
            QMessageBox.warning(self, 'error', f'You have indicate {folder_parent=} but the parent execution is not {Path(__file__).parent.stem}.')
            return

        # parameters
        self.db_path = db_path
        self.conn = None
        self.folder_parent = folder_parent
        self.folder_recipe = folder_recipe

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
            self.fill_recipe_details()
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

    def fill_recipe_details(self):
        cursor = self.conn.cursor()
        lyt = self.ui.categories_layout
        sql = 'select id, name, multi_tag from category'
        cursor.execute(sql)
        categories = cursor.fetchall()

        for category_id, category, multi_tag in categories:
            sql = f'''
            SELECT t.name, t.id, t.description
            FROM tag t
            WHERE t.category_id = {category_id}
            order by t.name
            '''
            cursor.execute(sql)
            tags = cursor.fetchall()
            ccb = CheckComboBox('Select...', multiSelect=multi_tag)
            ccb.addItems(tags)
            lyt.addRow(QLabel(category), ccb)

    def get_values(self):

        elements = {
            'name'          :self.ui.name.text().strip(),
            'time'          :self.ui.time.value(),
            'rate'          :self.ui.rate.currentText(),
            'description'   :self.ui.description.toPlainText().strip(),
            'created_at'    :self.ui.created_at.dateTime(),
            'updated_at'    :self.ui.updated_at.dateTime(),
            'nb_peoples'    :self.ui.nb_peoples.value(),
            'ingredients'   :self.ui.ingrdts_model.stringList(),
            'steps'         :self.ui.steps_model.stringList(),
            'images'        :self.ui.images.selected_images,
            'tags'          :{}
        }

        for row in range(self.ui.categories_layout.rowCount()):
            label = self.ui.categories_layout.itemAt(row, QFormLayout.ItemRole.LabelRole).widget()
            tags = self.ui.categories_layout.itemAt(row, QFormLayout.ItemRole.FieldRole).widget()

            elements['tags'][label.text()] = tags.selectedValues()

        return elements

    def submit(self):
        values = self.get_values()


        # field obligate to be feel
        obligate_fields = ['name', 'created_at', 'updated_at',
                           'nb_peoples', 'ingredients', 'steps']
        # check obligate fields
        wrong_field = []
        for obligate_field in obligate_fields:
            if  not values[obligate_field]:
                wrong_field.append(obligate_field)

        # alert and stop if some not good
        if wrong_field:
            QMessageBox.warning(self, "Warning", "Some obligate fields are not fill: "+ ', '.join(wrong_field))
            return

        overwrite = QMessageBox.question(
                        self, "Save this recipe in the database ?",
                        f"Are you sure that all is well set before push it ?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
        if overwrite == QMessageBox.StandardButton.No:
            return

        path_recipe = self.create_recipe(values['name'],values['nb_peoples'],values['ingredients'],values['steps'],
                                         overwrite=-1)
        # if error occure, don't continue
        if path_recipe == -1:
            return

        self.save_images(values['images'], to_path=Path(__file__).parent.parent / f'asset/image/recipe/{values['name'].lower()}')

        values['path'] = str(Path(self.folder_parent) / path_recipe)
        self.insert_recipe_to_db(self.conn, values)

    def create_recipe(self, name, nb_peoples, ingredients, steps, overwrite=-1):
        """overwrite -1=non, 0=if user agree, 1=yes"""
        content = {
            "nb_peoples":nb_peoples,
            "ingredients":ingredients,
            "steps":steps
        }
        path = Path(f'./{self.folder_recipe}/{name.lower()}.json')
        if path.exists():
            if overwrite == -1:
                QMessageBox.critical(self, 'Recipe already exist', 'A recipe with this name already exist. Please find another name.')
                return -1
            elif overwrite == 0:
                overwrite = QMessageBox.question(
                    self, "Overwrite Recipe",
                    f"A recipe is already present with the name {name}. Do you want to overwrite it ?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if overwrite == QMessageBox.StandardButton.No:
                    return -1

        with open(path, 'w') as file:
            json.dump(content, file, indent=4)
        return path

    def insert_recipe_to_db(self, conn, values):
        try:
            cursor = conn.cursor()

            # Insert the recipe
            created_at = values['created_at'].toString("yyyy-MM-dd HH:mm:ss")
            updated_at = values['updated_at'].toString("yyyy-MM-dd HH:mm:ss")
            cursor.execute("""
                INSERT INTO recipe (name, url, rating, time, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                values['name'].capitalize(),
                str(values['path']),  # chemin JSON comme URL
                int(values.get('rate', -1)),
                int(values.get('time', -1)),
                values.get('description', ''),
                created_at,
                updated_at
            ))

            recipe_id = cursor.lastrowid

            # Insert images
            for image_path in values.get('images', []):
                cursor.execute("""
                    INSERT INTO image (recipe_id, url, alt_text, created_at)
                    VALUES (?, ?, ?, ?)
                """, (
                    recipe_id,
                    image_path,
                    f"Image de {values['name']}",
                    created_at
                ))

            # Insert the tags
            for tag_name, tag_ids in values.get('tags', {}).items():
                for tag_id in tag_ids:
                    cursor.execute("""
                        INSERT OR IGNORE INTO recipeTag (recipe_id, tag_id)
                        VALUES (?, ?)
                    """, (recipe_id, tag_id))

            conn.commit()
            QMessageBox.information(
                self,
                "Recipe Saved",
                f"Recipe « {values['name']} » has been pushed successfully.",
                QMessageBox.StandardButton.Ok
            )
            self.clear_all_fields()
        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Error", f"Push failed: {e}")

    def clear_all_fields(self):
        # Clear simple text fields
        self.ui.name.clear()
        self.ui.time.setValue(0)
        self.ui.description.clear()

        # Reset ComboBox (rate)
        self.ui.rate.setCurrentIndex(0)

        # Reset SpinBox (number of people)
        self.ui.nb_peoples.setValue(4)

        # Reset DateTimeEdit for updated_at to current time
        self.ui.updated_at.setDateTime(QDateTime.currentDateTime())

        # Clear ingredients and steps lists
        self.ui.ingrdts_model.setStringList([])
        self.ui.steps_model.setStringList([])

        # Clear selected images and refresh the grid
        self.ui.images.selected_images.clear()
        self.ui.images._refresh_grid()

        # Uncheck all tags in CheckComboBoxes
        for row in range(self.ui.categories_layout.rowCount()):
            widget = self.ui.categories_layout.itemAt(row, QFormLayout.ItemRole.FieldRole).widget()
            if isinstance(widget, CheckComboBox):
                widget.clearSelection()

        # Optionally reset the scroll position of the image section
        self.ui.images.scroll.verticalScrollBar().setValue(0)

    def save_images(self, images, to_path):
        to_path = Path(to_path)
        to_path.mkdir(parents=True, exist_ok=True)

        img_idx = 0
        for image in images:
            new_img_path = to_path / f'{img_idx}.jpg'

            while new_img_path.exists():
                img_idx +=1
                new_img_path = to_path / f'{img_idx}.jpg'

            shutil.copy2(image, new_img_path)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = NewRecipe(folder_parent='bdd', folder_recipe='recipes')
    window.show()
    sys.exit(app.exec())
