import sys
import os
import shutil
import sqlite3
import requests
import yaml
import pandas as pd
import tempfile
import pydot
from pathlib import Path
from io import BytesIO
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QTreeWidget, QTreeWidgetItem,
    QTableView, QSplitter, QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit,
    QPushButton, QLabel, QMenuBar, QStatusBar, QMessageBox, QSizePolicy, QStyle,
    QInputDialog, QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QCheckBox, QMenu,
    QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsTextItem, QStyledItemDelegate
)
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QVariant, QUrl, QPointF
from PyQt6.QtGui import QPixmap, QAction, QSyntaxHighlighter, QTextCharFormat, QFont, QColor, QIcon, QDesktopServices, QBrush, QPen
from pygments import lex
from pygments.lexers.sql import SqlLexer
from pygments.token import Token

class PygmentsHighlighter(QSyntaxHighlighter):
    def __init__(self, parent):
        super().__init__(parent.document())
        self.lexer = SqlLexer()

        # mapping des types Pygments → formats Qt
        self.formats = {}
        def _fmt(color_name, bold=False):
            f = QTextCharFormat()
            if bold: f.setFontWeight(QFont.Weight.Bold)
            f.setForeground(QColor(color_name))
            return f


        self.formats[Token.Keyword] = _fmt("lightBlue", bold=True)

        # under categories
        self.formats[Token.Keyword.Constant] = _fmt("lightGreen")
        self.formats[Token.Keyword.Declaration] = _fmt("lightBlue", bold=True)
        self.formats[Token.Keyword.Reserved] = _fmt("lightBlue", bold=True)
        self.formats[Token.Keyword.Type] = _fmt("lightPurple")

        # String literals
        self.formats[Token.Literal.String] = _fmt("lightOrange")

        # Comments
        self.formats[Token.Comment] = _fmt("gray")


    def highlightBlock(self, text: str):
        index = 0
        for token, content in lex(text, self.lexer):
            fmt = self.formats.get(token)
            if fmt:
                self.setFormat(index, len(content), fmt)
            index += len(content)

class SQLiteModel(QAbstractTableModel):
    def __init__(self, data, headers, parent=None):
        super().__init__(parent)
        self._data = data
        self._headers = headers

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(self._headers)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return QVariant()
        value = self._data[index.row()][index.column()]
        if role == Qt.ItemDataRole.DecorationRole and isinstance(value, str) and value.startswith(('http://', 'https://')):
            if value.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                try:
                    resp = requests.get(value)
                    pix = QPixmap()
                    pix.loadFromData(resp.content)
                    return pix.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio)
                except Exception:
                    return QVariant()
        if role == Qt.ItemDataRole.DisplayRole:
            return str(value)
        return QVariant()

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return self._headers[section]
            else:
                return section + 1
        return QVariant()

class CenterDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        # centre horizontalement et verticalement
        option.displayAlignment = Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter

class UI():
    def __init__(self, main_window, title, width, height):
        # Initialize the main window
        self.main_window = main_window
        self.main_window.setWindowTitle(title)
        self.main_window.resize(width, height)

        # Build the structure
        self._central()
        self._menu()

    def _central(self):
        # Central widget
        central = QWidget()
        layout = QVBoxLayout()
        central.setLayout(layout)
        self.main_window.setCentralWidget(central)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(self.splitter)

        # add childs
        self._left(self.splitter)
        self._right(self.splitter)

    def _left(self, parent):
        # Right side: content and query area
        left_widget = QWidget()
        self.left_layout = QVBoxLayout()
        left_widget.setLayout(self.left_layout)
        parent.addWidget(left_widget)

        # add childs
        self._tree(self.left_layout)
        # self._query_area(self.right_layout)

    def _tree(self, parent, title="Database Structure"):
        # Database structure tree
        self.tree_layout = QVBoxLayout()

        # tree
        self.tree = QTreeWidget()

        # --- enable context menu on tree ---
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.main_window.on_tree_context_menu)

        self.tree.setHeaderLabel(title)
        self.tree.setUniformRowHeights(True)
        self.tree.setIndentation(16)

        self.tree.itemClicked.connect(self.main_window.on_tree_item_clicked)

        #buttons layout
        self.tree_button_layout = QHBoxLayout()

        # button open
        self.tree_button_open = QPushButton("Open")
        self.tree_button_open.clicked.connect(self.tree.expandAll)

        # button close
        self.tree_button_close = QPushButton("Close")
        self.tree_button_close.clicked.connect(self.tree.collapseAll)

        # add to layouts
        self.tree_button_layout.addWidget(self.tree_button_close)
        self.tree_button_layout.addWidget(self.tree_button_open)

        self.tree_layout.addWidget(self.tree)
        self.tree_layout.addLayout(self.tree_button_layout)

        parent.addLayout(self.tree_layout)

    def _update_size_tree(self):
        self.tree.expandAll()  # ensures all items are open
        self.splitter.setStretchFactor(0, 0) # Desactivate automatic stretch on the tree
        self.splitter.setStretchFactor(1, 1) # allow the right part to take all the space

    def _right(self, parent):
        # Right side: content and query area
        right_widget = QWidget()
        self.right_layout = QVBoxLayout()
        right_widget.setLayout(self.right_layout)
        parent.addWidget(right_widget)

        # add childs
        self._table_view(self.right_layout)
        self._query_area(self.right_layout)

    def _table_view(self, parent):
        # Table view
        self.table_view = QTableView()
        self.table_view.setItemDelegate(CenterDelegate(self.table_view))
        parent.addWidget(self.table_view)

    def _query_area(self, parent):
        # Query area
        self.query_layout = QVBoxLayout()

        self.query_edit = QPlainTextEdit()
        self.query_edit.setPlaceholderText("Enter SQL query here...")
        self.highlighter = PygmentsHighlighter(self.query_edit)

        self.query_button_layout = QHBoxLayout()

        self.query_button_execute = QPushButton("Execute")
        self.query_button_execute.clicked.connect(self.main_window.execute_query)

        self.query_button_save = QPushButton("Save Query")
        self.query_button_save.clicked.connect(lambda: self.main_window.save_query(self.query_edit.toPlainText()))

        self.query_button_layout.addWidget(self.query_button_execute)
        self.query_button_layout.addWidget(self.query_button_save)

        self.query_layout.addWidget(self.query_edit)
        self.query_layout.addLayout(self.query_button_layout)
        parent.addLayout(self.query_layout)

    def _menu(self):
        m = self.main_window.menuBar()

        # --- File Menu ---
        file_menu = m.addMenu("File")

        new_action = QAction("New Database...", self.main_window)
        new_action.triggered.connect(self.main_window.new_database)
        file_menu.addAction(new_action)

        open_action = QAction("Open Database...", self.main_window)
        open_action.triggered.connect(self.main_window.open_database)
        file_menu.addAction(open_action)

        close_action = QAction("Close Database", self.main_window)
        close_action.setEnabled(False)
        close_action.triggered.connect(self.main_window.close_database)
        file_menu.addAction(close_action)
        self.main_window.actions['close_db'] = close_action

        file_menu.addSeparator()

        save_as_action = QAction("Save Database As...", self.main_window)
        save_as_action.setEnabled(False)
        save_as_action.triggered.connect(self.main_window.save_database_as)
        file_menu.addAction(save_as_action)
        self.main_window.actions['save_as'] = save_as_action

        file_menu.addSeparator()

        import_csv_action = QAction("Import Table from CSV...", self.main_window)
        import_csv_action.setEnabled(False)
        import_csv_action.triggered.connect(self.main_window.import_csv)
        file_menu.addAction(import_csv_action)
        self.main_window.actions['import_csv'] = import_csv_action

        export_csv_action = QAction("Export Table to CSV...", self.main_window)
        export_csv_action.setEnabled(False)
        export_csv_action.triggered.connect(self.main_window.export_csv)
        file_menu.addAction(export_csv_action)
        self.main_window.actions['export_csv'] = export_csv_action

        file_menu.addSeparator()

        export_dump_action = QAction("Export SQL Dump...", self.main_window)
        export_dump_action.setEnabled(False)
        export_dump_action.triggered.connect(self.main_window.export_sql_dump)
        file_menu.addAction(export_dump_action)
        self.main_window.actions['export_dump'] = export_dump_action

        file_menu.addSeparator()

        self.recent_menu = file_menu.addMenu("Recent Files")

        file_menu.addSeparator()

        exit_action = QAction("Exit", self.main_window)
        exit_action.triggered.connect(self.main_window.close)
        file_menu.addAction(exit_action)


        # --- View Menu ---
        view_menu = m.addMenu("View")

        toggle_tree = QAction("Show Structure", self.main_window, checkable=True)
        toggle_tree.setChecked(True)
        toggle_tree.triggered.connect(lambda checked: self.main_window.toggle_panel('tree', checked))
        view_menu.addAction(toggle_tree)

        toggle_sql = QAction("Show SQL Editor", self.main_window, checkable=True)
        toggle_sql.setChecked(True)
        toggle_sql.triggered.connect(lambda checked: self.main_window.toggle_panel('sql', checked))
        view_menu.addAction(toggle_sql)

        view_menu.addSeparator()

        zoom_in = QAction("Zoom In", self.main_window)
        zoom_in.triggered.connect(self.main_window.zoom_in)
        view_menu.addAction(zoom_in)

        zoom_out = QAction("Zoom Out", self.main_window)
        zoom_out.triggered.connect(self.main_window.zoom_out)
        view_menu.addAction(zoom_out)

        view_menu.addSeparator()

        dark_mode = QAction("Dark Mode", self.main_window, checkable=True)
        dark_mode.triggered.connect(self.main_window.toggle_dark_mode)
        view_menu.addAction(dark_mode)


        # --- Query Menu ---
        query_menu = m.addMenu("Query")

        for name, snippet in [
            ("Select", "SELECT *\nFROM table_name;"),
            ("Insert", "INSERT INTO table_name (col1, col2) VALUES (v1, v2);"),
            ("Update", "UPDATE table_name\nSET col = value\nWHERE condition;"),
            ("Delete", "DELETE FROM table_name\nWHERE condition;")
        ]:
            act = QAction(name, self.main_window)
            act.triggered.connect(lambda _, q=snippet: self.main_window.on_menu_query_clicked(q))
            query_menu.addAction(act)

        query_menu.addSeparator()

        history_menu = query_menu.addMenu("History")
        clear_history = QAction("Clear History", self.main_window)
        clear_history.triggered.connect(self.main_window.clear_query_history)
        history_menu.addAction(clear_history)
        self.history_menu = history_menu

        query_menu.addSeparator()

        self.sub_query_menu = query_menu.addMenu("Customs")


        # --- Tools Menu ---
        tools_menu = m.addMenu("Tools")

        run_script = QAction("Execute SQL Script...", self.main_window)
        run_script.triggered.connect(self.main_window.execute_script)
        tools_menu.addAction(run_script)

        er_diagram = QAction("Generate ER Diagram...", self.main_window)
        er_diagram.triggered.connect(self.main_window.generate_er_diagram)
        tools_menu.addAction(er_diagram)


        # --- Help Menu ---
        help_menu = m.addMenu("Help")

        docs = QAction("Documentation", self.main_window)
        docs.triggered.connect(lambda: QDesktopServices.openUrl(QUrl("https://your.docs.url/")))
        help_menu.addAction(docs)

        report = QAction("Report Issue...", self.main_window)
        report.triggered.connect(lambda: QDesktopServices.openUrl(QUrl("https://your.issue.tracker/")))
        help_menu.addAction(report)

        help_menu.addSeparator()

        about = QAction("About", self.main_window)
        about.triggered.connect(self.main_window.show_about)
        help_menu.addAction(about)




    def add_query_menu(self, query_name, query):
        # Create submenu under self.ui.sub_query_menu
        sub_menu = self.sub_query_menu.addMenu(query_name)

        use = QAction("Use", sub_menu)
        use.triggered.connect(lambda checked, q=query: self.main_window.on_menu_query_clicked(q))
        sub_menu.addAction(use)

        delete = QAction("Delete", sub_menu)
        delete.triggered.connect(lambda checked, qn=query_name: self.main_window.delete_query(qn))
        sub_menu.addAction(delete)

    def delete_query_menu(self, query_name):
        # Find the submenu by title and remove it
        menus = self.sub_query_menu.actions()
        for action in menus:
            if action.menu() and action.text() == query_name:
                # Remove this submenu action
                self.sub_query_menu.removeAction(action)
                # Optionally delete it (if needed)
                action.menu().deleteLater()
                action.deleteLater()
                break


class DBManager(QMainWindow):
    CONFIG = Path('./') / '.db_manager_config.yaml'

    def __init__(self, width=1200, height=800, title='Database Manager', **kwargs):
        super().__init__()

        # Initialize variables
        self.conn = None
        self.db_path = ''
        self.db_name = ''
        self.actions = {}

        # charge config (recent files, history)
        self.config = yaml.safe_load(self.CONFIG.read_text()) if self.CONFIG.exists() else {}

        # Build the structure
        self.ui = UI(self, title, width, height)

        self._status()
        self._load_recent_menu()

        # Open the data base
        self.open_database()

    def _status(self):
        # Status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)

    def open_database(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select SQLite Database", "", "SQLite Files (*.db *.sqlite)")
        if path:
            try:
                if self.conn:
                    self.conn.close()
                self.conn = sqlite3.connect(path)
                self.status.showMessage(f"Opened {path}")
                self.load_structure()
                self.db_path = path
                self.db_name = Path(path).name
                self.load_queries()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open database: {e}")
                self.db_path = ''
                self.db_name = ''
        else:
            self.db_path = ''
            self.db_name = ''


    def load_structure(self):
        if not self.conn:
            return
        self.ui.tree.clear()

        roots = {}

        cursor = self.conn.cursor()
        cursor.execute("SELECT name, type, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' AND sql NOT NULL ORDER BY type")
        for name, typ, sql in cursor.fetchall():
            if typ not in roots:
                roots[typ] = QTreeWidgetItem(self.ui.tree, [typ.capitalize() + "s"])
                font = roots[typ].font(0)
                font.setPointSize(font.pointSize() + 1)
                font.setBold(True)
                roots[typ].setFont(0, font)

            parent = QTreeWidgetItem(
                roots[typ],
                [name]
            )

            # columns
            pr = self.conn.cursor()
            pr.execute(f"PRAGMA table_info('{name}')")
            for cid, col_name, col_type, notnull, dflt, pk in pr.fetchall():
                QTreeWidgetItem(parent, [f"{col_name} ({col_type})"])

        self.ui._update_size_tree()

    def on_tree_item_clicked(self, item, col):
        parent = item.parent()
        if parent and parent.text(0) == "Tables":
            table = item.text(0)
            self.display_table(table)

    def display_table(self, table):
        query = f"SELECT * FROM {table}"
        cursor = self.conn.cursor()
        try:
            cursor.execute(query)
            data = cursor.fetchall()
            headers = [d[0] for d in cursor.description]
            model = SQLiteModel(data, headers)
            self.ui.table_view.setModel(model)
            self.status.showMessage(f"Displayed table {table} with {len(data)} rows")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to display table: {e}")

    def load_queries(self):
        if not self.db_path or not self.db_name:
            return

        queries = yaml.safe_load(open(Path(self.db_path).with_suffix('.yaml'), 'r')) or {}

        for query_name, query in queries.items():
            self.ui.add_query_menu(query_name, query)




    def on_menu_query_clicked(self, query):
        self.ui.query_edit.setPlainText(query)

    def save_query(self, query):
        if not self.db_path or not self.db_name:
            QMessageBox.warning(self, "No Database", "Please open a database first.")
            return
        if not query.strip():
            QMessageBox.warning(self, "Empty Query", "Query cannot be empty.")
            return

        yaml_file = Path(self.db_path).with_suffix('.yaml')
        queries = {}
        if yaml_file.exists():
            queries = yaml.safe_load(open(yaml_file, 'r')) or {}

        query_name, ok = QInputDialog.getText(self, "Save Query", "Enter a name for the query:")
        query_name = query_name.strip()

        if query_name in queries:
            reply = QMessageBox.question(
                self,
                "Overwrite Query",
                f"A query named '{query_name}' already exists. Do you want to overwrite it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
            elif reply == QMessageBox.StandardButton.Yes:
                self.ui.delete_query_menu(query_name)  # Remove the old query from the menu

        if ok and query_name:
            queries[query_name] = query
            with open(yaml_file, 'w') as f:
                yaml.safe_dump(queries, f)
            QMessageBox.information(self, "Query Saved", f"Query '{query_name}' saved successfully.")
            self.ui.add_query_menu(query_name, query)

    def execute_query(self):
        if not self.conn:
            QMessageBox.warning(self, "No Database", "Please open a database first.")
            return
        sql = self.ui.query_edit.toPlainText().strip()
        if not sql:
            return
        cursor = self.conn.cursor()
        try:
            cursor.execute(sql)
            if sql.lower().startswith('select'):
                data = cursor.fetchall()
                headers = [d[0] for d in cursor.description]
                model = SQLiteModel(data, headers)
                self.ui.table_view.setModel(model)
                self.status.showMessage(f"Query returned {len(data)} rows")
            else:
                self.conn.commit()
                self.load_structure()
                self.status.showMessage(f"Executed: {sql.split()[0].upper()}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Query failed: {e}")

    def delete_query(self, query_name):
        reply = QMessageBox.question(
            self,
            "Delete Query",
            f"Are you sure you want to delete the query '{query_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            yaml_file = Path(self.db_path).with_suffix('.yaml')
            if yaml_file.exists():
                queries = yaml.safe_load(open(yaml_file, 'r')) or {}
                if query_name in queries:
                    del queries[query_name]
                    with open(yaml_file, 'w') as f:
                        yaml.safe_dump(queries, f)
                    QMessageBox.information(self, "Query Deleted", f"Query '{query_name}' deleted successfully.")
                    # Refresh the queries menu after deletion
                    self.ui.delete_query_menu(query_name)

    def new_database(self):
        path, _ = QFileDialog.getSaveFileName(self, "Create New Database", "", "SQLite Files (*.db)")
        if not path:
            return
        # crée immédiatement le fichier + son YAML associé
        open(path, 'a').close()
        yaml_fn = Path(path).with_suffix('.yaml')
        if not yaml_fn.exists():
            yaml_fn.write_text(yaml.safe_dump({}))
        self._connect_db(path)

    def open_database(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select SQLite Database", "", "SQLite Files (*.db *.sqlite)")
        if not path: return
        self._connect_db(path)

    def _connect_db(self, path):
        # fermeture éventuelle
        if self.conn:
            self.conn.close()
        # ouverture
        self.conn = sqlite3.connect(path)
        self.db_path = path
        self.db_name = Path(path).name
        self.status.showMessage(f"Opened {self.db_name}")
        # active les actions
        for k in ('close_db','save_as','import_csv','export_csv','export_dump'):
            self.actions[k].setEnabled(True)
        self.actions['export_dump'].setEnabled(True)
        self._add_to_recent(path)
        self.load_structure()
        self.load_queries()

    def close_database(self):
        if self.conn:
            self.conn.close()
        self.conn = None
        self.db_path = ''
        self.db_name = ''
        # VIDE l'arbre et la table
        self.ui.tree.clear()
        self.ui.table_view.setModel(None)
        self.status.showMessage("Database closed")
        # désactive actions
        for k in ('close_db','save_as','import_csv','export_csv','export_dump'):
            self.actions[k].setEnabled(False)

    def save_database_as(self):
        target, _ = QFileDialog.getSaveFileName(self, "Save Database As", Path(self.db_path).name, "SQLite Files (*.db)")
        if not target: return
        # utilise SQLite backup API
        dest = sqlite3.connect(target)
        with dest:
            self.conn.backup(dest)
        dest.close()
        self.status.showMessage(f"Saved copy to {target}")

    def import_csv(self):
        csvf, _ = QFileDialog.getOpenFileName(self, "Import CSV", "", "CSV Files (*.csv)")
        if not csvf: return
        tbl, ok = QInputDialog.getText(self, "Table Name", "Enter table name to create/import:")
        if not ok or not tbl.strip(): return
        df = pd.read_csv(csvf)
        # suppression si existe
        self.conn.execute(f"DROP TABLE IF EXISTS {tbl}")
        # création dynamique
        cols = ", ".join(f"'{c}' TEXT" for c in df.columns)
        self.conn.execute(f"CREATE TABLE {tbl} ({cols})")
        # insertion
        df.to_sql(tbl, self.conn, if_exists='append', index=False)
        self.conn.commit()
        self.load_structure()
        self.status.showMessage(f"Imported {len(df)} rows into {tbl}")

    def export_csv(self):
        tbl, ok = QInputDialog.getText(self, "Export CSV", "Enter table name to export:")
        if not ok or not tbl.strip():
            return
        try:
            df = pd.read_sql_query(f"SELECT * FROM {tbl}", self.conn)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Table '{tbl}' does not exist.\n{e}")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save CSV", f"{tbl}.csv", "CSV Files (*.csv)")
        if not path:
            return
        df.to_csv(path, index=False)
        self.status.showMessage(f"Exported {tbl} to {path}")

    # ---- Recent files ----
    def _add_to_recent(self, path):
        recent = self.config.get('recent', [])
        if path in recent: recent.remove(path)
        recent.insert(0, path)
        self.config['recent'] = recent[:10]
        self.CONFIG.write_text(yaml.safe_dump(self.config))
        self._load_recent_menu()

    def _load_recent_menu(self):
        self.ui.recent_menu.clear()
        for p in self.config.get('recent', []):
            act = QAction(Path(p).name, self)
            act.triggered.connect(lambda _, pp=p: self._connect_db(pp))
            self.ui.recent_menu.addAction(act)

    # ---- View ----
    def toggle_panel(self, panel, show):
        if panel == 'tree':
            # masque / affiche complètement le widget gauche (arbre + boutons)
            left = self.ui.splitter.widget(0)
            left.setVisible(show)
            # on rééquilibre l'espace
            if show:
                self.ui.splitter.setStretchFactor(0, 1)
                self.ui.splitter.setStretchFactor(1, 3)
            else:
                self.ui.splitter.setStretchFactor(0, 0)
                self.ui.splitter.setStretchFactor(1, 1)
        elif panel == 'sql':
            # masque l'ensemble du panneau SQL (éditeur + boutons)
            right = self.ui.splitter.widget(1)
            right.setVisible(show)
            if show:
                self.ui.splitter.setStretchFactor(0, 1)
                self.ui.splitter.setStretchFactor(1, 3)
            else:
                self.ui.splitter.setStretchFactor(0, 1)
                self.ui.splitter.setStretchFactor(1, 0)

    def on_tree_context_menu(self, pos):
        item = self.ui.tree.itemAt(pos)
        if not item:
            return
        menu = QMenu(self.ui.tree)
        parent = item.parent()

        # Clic-droit sur une table
        if parent and parent.text(0) == "Tables":
            tbl = item.text(0)
            menu.addAction("Show Data", lambda: self.display_table(tbl))
            menu.addAction("Describe Table", lambda: self.describe_table(tbl))

        # Clic-droit sur une colonne
        elif parent and parent.parent() and parent.parent().text(0) == "Tables":
            tbl = parent.text(0)
            col = item.text(0).split(' ')[0]
            menu.addAction("Copy Column Name", lambda: QApplication.clipboard().setText(col))
            menu.addAction(f"Show Data (WHERE {col}=…)", lambda: self.display_table_filtered(tbl, col))

        else:
            return

        menu.exec(self.ui.tree.viewport().mapToGlobal(pos))

    def describe_table(self, table):
        # Affiche la structure d'une table
        cols = self.conn.execute(f"PRAGMA table_info('{table}')").fetchall()
        txt = "\n".join(f"{c[1]} ({c[2]}){' PK' if c[5] else ''}" for c in cols)
        QMessageBox.information(self, f"Structure of {table}", txt)

    def display_table_filtered(self, table, column):
        # Ouvre un dialog pour entrer une valeur, puis affiche SELECT * WHERE
        val, ok = QInputDialog.getText(self, "Filter", f"WHERE {column} =")
        if not ok:
            return
        query = f"SELECT * FROM {table} WHERE \"{column}\" = ?"
        cursor = self.conn.cursor()
        cursor.execute(query, (val,))
        data = cursor.fetchall()
        hdr = [d[0] for d in cursor.description]
        self.ui.table_view.setModel(SQLiteModel(data, hdr))
        self.status.showMessage(f"{len(data)} rows WHERE {column}='{val}'")

    def zoom_in(self):
        f = self.ui.query_edit.font()
        f.setPointSize(f.pointSize()+1)
        self.ui.query_edit.setFont(f)

    def zoom_out(self):
        f = self.ui.query_edit.font()
        f.setPointSize(max(6, f.pointSize()-1))
        self.ui.query_edit.setFont(f)

    def toggle_dark_mode(self, on):
        if on:
            self.setStyleSheet("QWidget{background:#2b2b2b;color:#f0f0f0;}QLineEdit,QPlainTextEdit{background:#3c3f41;}")
        else:
            self.setStyleSheet("")

    # ---- Query history ----
    def clear_query_history(self):
        yaml_file = Path(self.db_path).with_suffix('.yaml')
        if yaml_file.exists():
            yaml_file.unlink()
        # efface menu customs
        for act in list(self.ui.sub_query_menu.actions()):
            self.ui.sub_query_menu.removeAction(act)
        QMessageBox.information(self, "History", "Query history cleared.")

    # ---- Tools ----
    def execute_script(self):
        path, _ = QFileDialog.getOpenFileName(self, "SQL Script", "", "SQL Files (*.sql)")
        if not path: return
        sql = open(path).read()
        try:
            self.conn.executescript(sql)
            self.conn.commit()
            self.load_structure()
            QMessageBox.information(self, "Script", "Script executed successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def generate_er_diagram(self):
        """Génère un diagramme ER Mermaid, l'affiche et propose de l'exporter en .md."""
        if not self.conn:
            QMessageBox.warning(self, "No Database", "Please open a database first.")
            return

        cur = self.conn.cursor()
        # 1) Tables utilisateur
        cur.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name"
        )
        tables = [row[0] for row in cur.fetchall()]
        if not tables:
            QMessageBox.information(self, "ER Diagram", "Aucune table trouvée.")
            return

        # 2) Récupère toutes les clés étrangères
        #    tuple: (src_table, dst_table, src_col, dst_col)
        fks = []
        for src in tables:
            cur.execute(f"PRAGMA foreign_key_list('{src}')")
            for fk in cur.fetchall():
                dst = fk[2]      # table référencée
                col_src = fk[3]  # colonne dans src
                col_dst = fk[4]  # colonne dans dst
                fks.append((src, dst, col_src, col_dst))

        # 3) Construit le bloc Mermaid ER
        lines = ["```mermaid", "erDiagram"]
        # entités
        for t in tables:
            lines.append(f"    {t} {{")
            cur.execute(f"PRAGMA table_info('{t}')")
            for cid, name, ctype, notnull, dflt, pk in cur.fetchall():
                pk_mark = " PK" if pk else ""
                lines.append(f"        {ctype} {name}{pk_mark}")
            lines.append("    }")
        lines.append("")  # ligne vide

        # relations 1–n : la table référencée ||--o{ la table qui référence
        for src, dst, col_src, col_dst in fks:
            # dst = parent, src = child
            lines.append(f"    {dst} ||--o{{ {src} : \"{col_dst} → {col_src}\"")
        lines.append("```")

        mermaid_md = "\n".join(lines)

        # 4) Affiche + option export
        dlg = QDialog(self)
        dlg.setWindowTitle("ER Diagram (Mermaid)")
        layout = QVBoxLayout(dlg)

        layout.addWidget(QLabel(
            "Voici le diagramme ER au format Mermaid Markdown. Vous pouvez copier/coller\n"
            "ou l'exporter en `.md` pour le rendre sur GitHub, GitLab, etc."
        ))

        editor = QPlainTextEdit(dlg)
        editor.setPlainText(mermaid_md)
        editor.setReadOnly(True)
        layout.addWidget(editor)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Close
        )
        layout.addWidget(btns)

        def save_md():
            path, _ = QFileDialog.getSaveFileName(
                dlg,
                "Save Mermaid Diagram",
                f"{self.db_name}_ER.md",
                "Markdown Files (*.md);;All Files (*)"
            )
            if path:
                try:
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(mermaid_md)
                    QMessageBox.information(dlg, "Saved", f"ER diagram saved to:\n{path}")
                except Exception as e:
                    QMessageBox.critical(dlg, "Error", f"Failed to save:\n{e}")

        btns.accepted.connect(save_md)
        btns.rejected.connect(dlg.reject)

        dlg.resize(600, 500)
        dlg.exec()


    def sync_data(self):
        QMessageBox.information(self, "Sync", "Synchronize feature not yet implemented.")

    # ---- Help/About ----
    def show_about(self):
        QMessageBox.about(self, "About", "Database Manager v1.0\n© 2025")

    def export_sql_dump(self):
        if not self.conn:
            QMessageBox.warning(self, "No Database", "Please open a database first.")
            return

        # Choix du fichier .txt
        path, _ = QFileDialog.getSaveFileName(
            self, "Export SQL Dump", f"{self.db_name}_dump.txt", "Text Files (*.txt)"
        )
        if not path:
            return

        try:
            with open(path, 'w', encoding='utf-8') as f:
                cursor = self.conn.cursor()
                # 1) Structure : CREATE statements
                cursor.execute(
                    "SELECT type, name, sql FROM sqlite_master "
                    "WHERE type IN ('table','index','trigger','view') AND sql NOT NULL"
                )
                for typ, name, sql in cursor.fetchall():
                    f.write(f"-- {typ.upper()} {name}\n")
                    f.write(sql.strip() + ";\n\n")

                # 2) Données : pour chaque table, on émet des INSERT
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name NOT LIKE 'sqlite_%'"
                )
                tables = [r[0] for r in cursor.fetchall()]
                for tbl in tables:
                    cursor.execute(f"PRAGMA table_info('{tbl}')")
                    cols = [col[1] for col in cursor.fetchall()]
                    col_list = ", ".join(f"\"{c}\"" for c in cols)

                    cursor.execute(f"SELECT * FROM \"{tbl}\"")
                    rows = cursor.fetchall()
                    if not rows:
                        continue

                    f.write(f"-- Dumping data for table {tbl}\n")
                    for row in rows:
                        # on prépare chaque valeur pour SQL
                        vals = []
                        for v in row:
                            if v is None:
                                vals.append("NULL")
                            elif isinstance(v, (int, float)):
                                vals.append(str(v))
                            else:
                                escaped = str(v).replace("'", "''")
                                vals.append(f"'{escaped}'")
                        val_list = ", ".join(vals)
                        f.write(f"INSERT INTO \"{tbl}\" ({col_list}) VALUES ({val_list});\n")
                    f.write("\n")

            QMessageBox.information(self, "Export Successful", f"SQL dump saved to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Error while exporting SQL dump:\n{e}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = DBManager()
    window.show()
    sys.exit(app.exec())
