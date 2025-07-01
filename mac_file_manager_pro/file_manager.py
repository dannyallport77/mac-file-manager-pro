import sys
import os
import shutil
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QSplitter, QListView, QTreeView, QTableView, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileSystemModel, QAbstractItemView, QToolBar, QLabel, QStyle, QSlider, QMessageBox, QInputDialog, QAction, QComboBox, QStyledItemDelegate, QLineEdit, QMenu
)
from PyQt5.QtCore import Qt, QDir, QModelIndex, QSize, QMimeData, QSortFilterProxyModel
from PyQt5.QtGui import QIcon, QPixmap, QDrag, QKeySequence, QMovie, QPainter, QTextDocument, QColor
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
import mimetypes
import re

# --- Helper for file type icons ---
def get_icon_for_file(path):
    if os.path.isdir(path):
        return QApplication.style().standardIcon(QStyle.SP_DirIcon)
    ext = os.path.splitext(path)[1].lower()
    if ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif']:
        return QApplication.style().standardIcon(QStyle.SP_FileIcon)
    if ext in ['.mp4', '.mov', '.avi', '.mkv']:
        return QApplication.style().standardIcon(QStyle.SP_MediaPlay)
    return QApplication.style().standardIcon(QStyle.SP_FileIcon)

# --- File Panel Widget ---
class HighlightDelegate(QStyledItemDelegate):
    def __init__(self, parent=None, get_thumb_size=lambda: 64, get_search_text=lambda: ""):
        super().__init__(parent)
        self.get_thumb_size = get_thumb_size
        self.get_search_text = get_search_text

    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        search = self.get_search_text().strip()
        if search:
            name = index.data(Qt.DisplayRole)
            # Highlight all matches (case-insensitive, wildcards)
            pattern = re.escape(search).replace(r'\*', '.*').replace(r'\?', '.')
            regex = re.compile(pattern, re.IGNORECASE)
            match = regex.search(name)
            if match:
                painter.save()
                rect = option.rect
                doc = QTextDocument()
                highlighted = regex.sub(lambda m: f'<span style="background-color: #ffff00;">{m.group(0)}</span>', name)
                doc.setHtml(highlighted)
                doc.setTextWidth(rect.width())
                painter.translate(rect.x(), rect.y() + self.get_thumb_size() + 2)
                doc.drawContents(painter)
                painter.restore()

class ThumbnailDelegate(QStyledItemDelegate):
    def __init__(self, parent=None, get_thumb_size=lambda: 64):
        super().__init__(parent)
        self.get_thumb_size = get_thumb_size

    def paint(self, painter, option, index):
        model = index.model()
        file_path = model.filePath(index)
        ext = os.path.splitext(file_path)[1].lower()
        thumb_size = self.get_thumb_size()
        pixmap = None
        if ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif']:
            pixmap = QPixmap(file_path).scaled(thumb_size, thumb_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        elif ext in ['.mp4', '.mov', '.avi', '.mkv']:
            # Try to extract a frame using ffmpeg
            import tempfile
            import os
            thumb_path = os.path.join(tempfile.gettempdir(), f"thumb_{os.path.basename(file_path)}.png")
            if not os.path.exists(thumb_path):
                try:
                    subprocess.run([
                        'ffmpeg', '-y', '-i', file_path, '-ss', '00:00:01.000', '-vframes', '1', thumb_path
                    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    pass
            if os.path.exists(thumb_path):
                pixmap = QPixmap(thumb_path).scaled(thumb_size, thumb_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            else:
                pixmap = QPixmap(thumb_size, thumb_size)
                pixmap.fill(Qt.black)
                icon = QApplication.style().standardIcon(QStyle.SP_MediaPlay)
                painter.save()
                icon.paint(painter, option.rect)
                painter.restore()
                return
        elif ext in ['.mp3', '.wav', '.aac', '.flac']:
            pixmap = QPixmap(thumb_size, thumb_size)
            pixmap.fill(Qt.darkGray)
            icon = QApplication.style().standardIcon(QStyle.SP_MediaVolume)
            painter.save()
            icon.paint(painter, option.rect)
            painter.restore()
            return
        else:
            pixmap = model.data(index, Qt.DecorationRole)
        painter.save()
        painter.drawPixmap(option.rect.x(), option.rect.y(), pixmap)
        painter.restore()
        QStyledItemDelegate.paint(self, painter, option, index)

class FilePanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.toolbar = QToolBar()
        self.layout.addWidget(self.toolbar)
        # Search and filter controls
        self.folder_search = QLineEdit()
        self.folder_search.setPlaceholderText('Search folders...')
        self.folder_search.textChanged.connect(self.filter_folders)
        self.layout.addWidget(self.folder_search)
        # Multi-type filter with icons
        self.file_filter_menu = QMenu()
        self.file_type_actions = {}
        type_icon_map = {
            'Images': QIcon.fromTheme('image-x-generic') or QApplication.style().standardIcon(QStyle.SP_FileIcon),
            'Video': QIcon.fromTheme('video-x-generic') or QApplication.style().standardIcon(QStyle.SP_MediaPlay),
            'Audio': QIcon.fromTheme('audio-x-generic') or QApplication.style().standardIcon(QStyle.SP_MediaVolume),
            'Archives': QIcon.fromTheme('package-x-generic') or QApplication.style().standardIcon(QStyle.SP_DirIcon),
            'Documents': QIcon.fromTheme('text-x-generic') or QApplication.style().standardIcon(QStyle.SP_FileIcon),
            'Code': QIcon.fromTheme('text-x-script') or QApplication.style().standardIcon(QStyle.SP_FileIcon),
            'Other': QIcon.fromTheme('application-octet-stream') or QApplication.style().standardIcon(QStyle.SP_FileIcon),
        }
        for t in ['Images', 'Video', 'Audio', 'Archives', 'Documents', 'Code', 'Other']:
            act = QAction(type_icon_map[t], t, self)
            act.setCheckable(True)
            act.setChecked(False)
            act.toggled.connect(self.filter_files)
            self.file_filter_menu.addAction(act)
            self.file_type_actions[t] = act
        self.file_filter_btn = QPushButton('Filter Types')
        self.file_filter_btn.setMenu(self.file_filter_menu)
        self.layout.addWidget(self.file_filter_btn)
        self.file_search = QLineEdit()
        self.file_search.setPlaceholderText('Search files...')
        self.file_search.textChanged.connect(self.filter_files)
        self.layout.addWidget(self.file_search)
        self.folder_selector = QComboBox()
        self.folder_selector.setEditable(True)
        self.folder_selector.setMinimumWidth(250)
        self.folder_selector.activated[str].connect(self.set_folder)
        self.toolbar.addWidget(self.folder_selector)
        self.back_btn = QPushButton('Back')
        self.back_btn.clicked.connect(self.go_back)
        self.toolbar.addWidget(self.back_btn)
        self.forward_btn = QPushButton('Forward')
        self.forward_btn.clicked.connect(self.go_forward)
        self.toolbar.addWidget(self.forward_btn)
        self.up_btn = QPushButton('Up')
        self.up_btn.clicked.connect(self.go_up)
        self.toolbar.addWidget(self.up_btn)
        self.bookmark_btn = QPushButton('Bookmark')
        self.bookmark_btn.clicked.connect(self.add_bookmark)
        self.toolbar.addWidget(self.bookmark_btn)
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(['Name', 'Size', 'Type', 'Date'])
        self.sort_combo.currentIndexChanged.connect(self.sort_views)
        self.toolbar.addWidget(QLabel('Sort by:'))
        self.toolbar.addWidget(self.sort_combo)
        self.view_mode_combo = QComboBox()
        self.view_mode_combo.addItems(['Icon', 'List', 'Column'])
        self.view_mode_combo.currentIndexChanged.connect(self.change_view_mode)
        self.toolbar.addWidget(QLabel('View:'))
        self.toolbar.addWidget(self.view_mode_combo)
        self.thumb_size = 64
        self.thumb_slider = QSlider(Qt.Horizontal)
        self.thumb_slider.setMinimum(32)
        self.thumb_slider.setMaximum(256)
        self.thumb_slider.setValue(self.thumb_size)
        self.thumb_slider.setTickInterval(16)
        self.thumb_slider.setTickPosition(QSlider.TicksBelow)
        self.thumb_slider.valueChanged.connect(self.set_thumb_size)
        self.toolbar.addWidget(QLabel('Thumbnail Size:'))
        self.toolbar.addWidget(self.thumb_slider)
        self.icon_size = self.thumb_size
        self.model = QFileSystemModel()
        self.model.setRootPath(QDir.rootPath())
        self.folder_proxy = QSortFilterProxyModel()
        self.folder_proxy.setSourceModel(self.model)
        self.folder_proxy.setFilterRole(QFileSystemModel.FilePathRole)
        self.folder_proxy.setFilterRegExp('')
        self.folder_proxy.setFilterKeyColumn(0)
        self.folder_proxy.setDynamicSortFilter(True)
        self.folder_proxy.setFilterAcceptsRow = lambda source_row, source_parent: self.model.isDir(self.model.index(source_row, 0, source_parent))
        self.file_proxy = QSortFilterProxyModel()
        self.file_proxy.setSourceModel(self.model)
        self.file_proxy.setFilterRole(QFileSystemModel.FilePathRole)
        self.file_proxy.setFilterRegExp('')
        self.file_proxy.setFilterKeyColumn(0)
        self.file_proxy.setDynamicSortFilter(True)
        self.file_proxy.setFilterAcceptsRow = self.file_accepts_row
        self.splitter = QSplitter(Qt.Vertical)
        self.folder_view = QListView()
        self.folder_view.setModel(self.folder_proxy)
        self.folder_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.folder_view.setViewMode(QListView.IconMode)
        self.folder_view.setIconSize(QSize(self.icon_size, self.icon_size))
        self.folder_view.setGridSize(QSize(self.icon_size+24, self.icon_size+36))
        self.folder_view.doubleClicked.connect(self.on_folder_double_click)
        self.file_view = QListView()
        self.file_view.setModel(self.file_proxy)
        self.file_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.file_view.setViewMode(QListView.IconMode)
        self.file_view.setIconSize(QSize(self.icon_size, self.icon_size))
        self.file_view.setGridSize(QSize(self.icon_size+24, self.icon_size+36))
        self.file_view.doubleClicked.connect(self.on_file_double_click)
        self.file_view.setItemDelegate(HighlightDelegate(get_thumb_size=lambda: self.thumb_size, get_search_text=lambda: self.file_search.text()))
        self.folder_tree = QTreeView()
        self.folder_tree.setModel(self.model)
        self.folder_tree.setRootIndex(self.model.index(QDir.homePath()))
        self.folder_tree.hide()
        self.file_tree = QTreeView()
        self.file_tree.setModel(self.model)
        self.file_tree.setRootIndex(self.model.index(QDir.homePath()))
        self.file_tree.hide()
        self.splitter.addWidget(self.folder_view)
        self.splitter.addWidget(self.file_view)
        self.layout.addWidget(self.splitter)
        self.current_path = QDir.homePath()
        self.history = []
        self.forward_history = []
        self.bookmarks = []
        self.setup_toolbar()
        self.populate_common_folders()
        self.update_folder_selector(self.current_path)
        self.update_views()
        self.folder_view.setDragEnabled(True)
        self.folder_view.setAcceptDrops(True)
        self.folder_view.setDropIndicatorShown(True)
        self.file_view.setDragEnabled(True)
        self.file_view.setAcceptDrops(True)
        self.file_view.setDropIndicatorShown(True)
        self.folder_view.viewport().installEventFilter(self)
        self.file_view.viewport().installEventFilter(self)
        self.folder_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.folder_view.customContextMenuRequested.connect(self.open_context_menu)
        self.file_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_view.customContextMenuRequested.connect(self.open_context_menu)
        self.preview_widget = QLabel()
        self.preview_widget.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.preview_widget)
        self.preview_widget.hide()
        self.media_player = None
        self.gif_movie = None
        self.last_played = None
        self.file_view.selectionModel().selectionChanged.connect(self.update_preview)

    def populate_common_folders(self):
        home = QDir.homePath()
        folders = [
            home,
            os.path.join(home, 'Desktop'),
            os.path.join(home, 'Documents'),
            os.path.join(home, 'Downloads'),
            '/Applications',
        ]
        for folder in folders:
            if os.path.isdir(folder):
                self.folder_selector.addItem(folder)

    def setup_toolbar(self):
        self.icon_action = QAction('Icon', self)
        self.icon_action.triggered.connect(lambda: self.set_view_mode('icon'))
        self.toolbar.addAction(self.icon_action)
        self.list_action = QAction('List', self)
        self.list_action.triggered.connect(lambda: self.set_view_mode('list'))
        self.toolbar.addAction(self.list_action)
        self.column_action = QAction('Columns', self)
        self.column_action.triggered.connect(lambda: self.set_view_mode('column'))
        self.toolbar.addAction(self.column_action)
        self.preview_action = QAction('Preview', self)
        self.preview_action.triggered.connect(lambda: self.set_view_mode('preview'))
        self.toolbar.addAction(self.preview_action)
        self.toolbar.addSeparator()
        self.plus_btn = QPushButton('+')
        self.plus_btn.clicked.connect(self.increase_icon_size)
        self.toolbar.addWidget(self.plus_btn)
        self.minus_btn = QPushButton('-')
        self.minus_btn.clicked.connect(self.decrease_icon_size)
        self.toolbar.addWidget(self.minus_btn)
        self.toolbar.addSeparator()
        self.open_action = QAction('Open...', self)
        self.open_action.triggered.connect(self.open_folder_dialog)
        self.toolbar.addAction(self.open_action)

    def set_view_mode(self, mode):
        self.view_mode = mode
        if mode == 'icon':
            self.folder_view.setViewMode(QListView.IconMode)
            self.folder_view.setIconSize(QSize(self.icon_size, self.icon_size))
            self.file_view.setViewMode(QListView.IconMode)
            self.file_view.setIconSize(QSize(self.icon_size, self.icon_size))
        elif mode == 'list':
            self.folder_view.setViewMode(QListView.ListMode)
            self.folder_view.setIconSize(QSize(32, 32))
            self.file_view.setViewMode(QListView.ListMode)
            self.file_view.setIconSize(QSize(32, 32))
        elif mode == 'column':
            # For simplicity, use list mode as column view is not native in QListView
            self.folder_view.setViewMode(QListView.ListMode)
            self.folder_view.setIconSize(QSize(32, 32))
            self.file_view.setViewMode(QListView.ListMode)
            self.file_view.setIconSize(QSize(32, 32))
        elif mode == 'preview':
            self.update_preview()

    def increase_icon_size(self):
        self.icon_size = min(256, self.icon_size + 16)
        self.folder_view.setIconSize(QSize(self.icon_size, self.icon_size))
        self.file_view.setIconSize(QSize(self.icon_size, self.icon_size))

    def decrease_icon_size(self):
        self.icon_size = max(16, self.icon_size - 16)
        self.folder_view.setIconSize(QSize(self.icon_size, self.icon_size))
        self.file_view.setIconSize(QSize(self.icon_size, self.icon_size))

    def go_up(self):
        parent = os.path.dirname(self.current_path)
        if parent and os.path.exists(parent):
            self.set_folder(parent)

    def open_folder_dialog(self):
        folder, ok = QInputDialog.getText(self, 'Open Folder', 'Enter folder path:', text=self.current_path)
        if ok and folder and os.path.isdir(folder):
            self.set_folder(folder)

    def update_folder_selector(self, path):
        if path not in [self.folder_selector.itemText(i) for i in range(self.folder_selector.count())]:
            self.folder_selector.addItem(path)
        self.folder_selector.setCurrentText(path)

    def go_back(self):
        if self.history:
            prev = self.history.pop()
            self.forward_history.append(self.current_path)
            self.set_folder(prev, add_to_history=False, clear_forward=False)

    def go_forward(self):
        if self.forward_history:
            next_path = self.forward_history.pop()
            self.history.append(self.current_path)
            self.set_folder(next_path, add_to_history=False, clear_forward=False)

    def add_bookmark(self):
        if self.current_path not in self.bookmarks:
            self.bookmarks.append(self.current_path)
            self.folder_selector.addItem(f"★ {self.current_path}")

    def update_views(self):
        idx = self.model.index(self.current_path)
        self.folder_view.setRootIndex(self.folder_proxy.mapFromSource(idx))
        self.file_view.setRootIndex(self.file_proxy.mapFromSource(idx))

    def sort_views(self):
        sort_col = 0
        order = Qt.AscendingOrder
        if self.sort_combo.currentText() == 'Name':
            sort_col = 0
        elif self.sort_combo.currentText() == 'Size':
            sort_col = 1
        elif self.sort_combo.currentText() == 'Type':
            sort_col = 2
        elif self.sort_combo.currentText() == 'Date':
            sort_col = 3
        self.folder_proxy.sort(sort_col, order)
        self.file_proxy.sort(sort_col, order)

    def set_folder(self, path, add_to_history=True, clear_forward=True):
        if not os.path.isdir(path):
            return
        if add_to_history and hasattr(self, 'current_path') and self.current_path != path:
            self.history.append(self.current_path)
        if clear_forward:
            self.forward_history.clear()
        self.current_path = path
        self.update_views()
        self.update_folder_selector(path)
        self.update_preview()

    def on_folder_double_click(self, index):
        src_idx = self.folder_proxy.mapToSource(index)
        path = self.model.filePath(src_idx)
        if os.path.isdir(path):
            self.set_folder(path)

    def on_file_double_click(self, index):
        src_idx = self.file_proxy.mapToSource(index)
        path = self.model.filePath(src_idx)
        self.open_file(path)

    def open_file(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext in ['.png', '.jpg', '.jpeg', '.bmp']:
            self.preview_widget.setPixmap(QPixmap(path).scaled(400, 400, Qt.KeepAspectRatio))
            self.preview_widget.show()
        elif ext == '.gif':
            if self.gif_movie:
                self.gif_movie.stop()
            self.gif_movie = QMovie(path)
            self.preview_widget.setMovie(self.gif_movie)
            self.gif_movie.start()
            self.preview_widget.show()
        elif ext in ['.mp4', '.mov', '.avi', '.mkv']:
            if self.media_player:
                self.media_player.stop()
            self.media_player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
            video_widget = QVideoWidget()
            self.media_player.setVideoOutput(video_widget)
            self.media_player.setMedia(QMediaContent(QUrl.fromLocalFile(path)))
            self.media_player.play()
            self.layout.addWidget(video_widget)
            video_widget.show()
            self.last_played = video_widget
        else:
            os.system(f'open "{path}"')

    def update_preview(self):
        if self.view_mode_combo.currentText().lower() != 'preview':
            self.preview_widget.hide()
            return
        indexes = self.file_view.selectedIndexes()
        if not indexes:
            self.preview_widget.hide()
            return
        path = self.model.filePath(indexes[0])
        ext = os.path.splitext(path)[1].lower()
        if ext in ['.png', '.jpg', '.jpeg', '.bmp']:
            self.preview_widget.setPixmap(QPixmap(path).scaled(400, 400, Qt.KeepAspectRatio))
            self.preview_widget.show()
        elif ext == '.gif':
            if self.gif_movie:
                self.gif_movie.stop()
            self.gif_movie = QMovie(path)
            self.preview_widget.setMovie(self.gif_movie)
            self.gif_movie.start()
            self.preview_widget.show()
        elif ext in ['.mp4', '.mov', '.avi', '.mkv']:
            if self.media_player:
                self.media_player.stop()
            self.media_player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
            video_widget = QVideoWidget()
            self.media_player.setVideoOutput(video_widget)
            self.media_player.setMedia(QMediaContent(QUrl.fromLocalFile(path)))
            self.media_player.play()
            self.layout.addWidget(video_widget)
            video_widget.show()
            self.last_played = video_widget
        else:
            self.preview_widget.hide()

    def open_context_menu(self, pos):
        menu = self.folder_view.createStandardContextMenu()
        menu.exec_(self.folder_view.viewport().mapToGlobal(pos))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Backspace:
            self.delete_selected()
        else:
            super().keyPressEvent(event)

    def delete_selected(self):
        indexes = self.folder_view.selectedIndexes() + self.file_view.selectedIndexes()
        if not indexes:
            return
        files = [self.model.filePath(idx) for idx in indexes]
        reply = QMessageBox.question(self, 'Delete', f'Delete {len(files)} item(s)?', QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            for f in files:
                try:
                    if os.path.isdir(f):
                        shutil.rmtree(f)
                    else:
                        os.remove(f)
                except Exception as e:
                    QMessageBox.warning(self, 'Error', str(e))
            self.model.refresh()

    def eventFilter(self, obj, event):
        # For box selection and drag
        return super().eventFilter(obj, event)

    def change_view_mode(self):
        mode = self.view_mode_combo.currentText().lower()
        if mode == 'icon':
            self.folder_view.show()
            self.file_view.show()
            self.folder_tree.hide()
            self.file_tree.hide()
            self.folder_view.setViewMode(QListView.IconMode)
            self.file_view.setViewMode(QListView.IconMode)
        elif mode == 'list':
            self.folder_view.show()
            self.file_view.show()
            self.folder_tree.hide()
            self.file_tree.hide()
            self.folder_view.setViewMode(QListView.ListMode)
            self.file_view.setViewMode(QListView.ListMode)
        elif mode == 'column':
            self.folder_view.hide()
            self.file_view.hide()
            self.folder_tree.show()
            self.file_tree.show()
            self.folder_tree.setRootIndex(self.model.index(self.current_path))
            self.file_tree.setRootIndex(self.model.index(self.current_path))

    def set_thumb_size(self, value):
        self.thumb_size = value
        self.icon_size = value
        self.file_view.setIconSize(QSize(self.icon_size, self.icon_size))
        self.folder_view.setIconSize(QSize(self.icon_size, self.icon_size))
        self.file_view.setGridSize(QSize(self.icon_size+24, self.icon_size+36))
        self.folder_view.setGridSize(QSize(self.icon_size+24, self.icon_size+36))
        self.file_view.viewport().update()
        self.folder_view.viewport().update()

    def filter_folders(self, text):
        # Case-insensitive, wildcard support
        pattern = re.escape(text)
        pattern = pattern.replace(r'\*', '.*').replace(r'\?', '.')
        self.folder_proxy.setFilterRegExp(f'(?i){pattern}')
        self.folder_view.viewport().update()
    def filter_files(self, text):
        pattern = re.escape(text)
        pattern = pattern.replace(r'\*', '.*').replace(r'\?', '.')
        self.file_proxy.setFilterRegExp(f'(?i){pattern}')
        self.file_view.viewport().update()

    def file_accepts_row(self, source_row, source_parent):
        index = self.model.index(source_row, 0, source_parent)
        if self.model.isDir(index):
            return False
        path = self.model.filePath(index)
        ext = os.path.splitext(path)[1].lower()
        selected_types = [t for t, act in self.file_type_actions.items() if act.isChecked()]
        if not selected_types:
            return True  # No filter, show all
        type_map = {
            'Images': ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp'],
            'Video': ['.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm'],
            'Audio': ['.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a'],
            'Archives': ['.zip', '.rar', '.tar', '.gz', '.bz2', '.7z', '.xz'],
            'Documents': ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.md', '.rtf', '.odt'],
            'Code': ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.cs', '.html', '.css', '.json', '.xml', '.sh', '.bat', '.php', '.rb', '.go', '.swift', '.kt', '.rs'],
        }
        for t in selected_types:
            if t == 'Other':
                all_exts = sum(type_map.values(), [])
                if ext not in all_exts:
                    return True
            elif ext in type_map[t]:
                return True
        return False

# --- Main Window ---
class FileManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Graphical File Manager')
        self.resize(1200, 700)
        self.central = QWidget()
        self.setCentralWidget(self.central)
        self.layout = QVBoxLayout(self.central)
        self.splitter = QSplitter(Qt.Horizontal)
        self.left_panel = FilePanel()
        self.right_panel = FilePanel()
        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.right_panel)
        self.layout.addWidget(self.splitter)
        self.move_copy_bar = QHBoxLayout()
        self.move_btn = QPushButton('MOVE')
        self.copy_btn = QPushButton('COPY')
        self.move_btn.setCheckable(True)
        self.copy_btn.setCheckable(True)
        self.move_btn.setChecked(True)
        self.move_btn.clicked.connect(self.set_move_mode)
        self.copy_btn.clicked.connect(self.set_copy_mode)
        self.move_copy_bar.addWidget(QLabel('Drag mode:'))
        self.move_copy_bar.addWidget(self.move_btn)
        self.move_copy_bar.addWidget(self.copy_btn)
        self.layout.addLayout(self.move_copy_bar)
        self.drag_mode = 'move'
        self.left_panel.folder_view.viewport().installEventFilter(self)
        self.right_panel.folder_view.viewport().installEventFilter(self)
        self.left_panel.file_view.viewport().installEventFilter(self)
        self.right_panel.file_view.viewport().installEventFilter(self)
        self.left_panel.folder_view.setDragDropMode(QAbstractItemView.DragDrop)
        self.right_panel.folder_view.setDragDropMode(QAbstractItemView.DragDrop)
        self.left_panel.file_view.setDragDropMode(QAbstractItemView.DragDrop)
        self.right_panel.file_view.setDragDropMode(QAbstractItemView.DragDrop)
        self.left_panel.folder_view.dragEnterEvent = self.dragEnterEvent
        self.right_panel.folder_view.dragEnterEvent = self.dragEnterEvent
        self.left_panel.file_view.dragEnterEvent = self.dragEnterEvent
        self.right_panel.file_view.dragEnterEvent = self.dragEnterEvent
        self.left_panel.folder_view.dropEvent = self.dropEvent
        self.right_panel.folder_view.dropEvent = self.dropEvent
        self.left_panel.file_view.dropEvent = self.dropEvent
        self.right_panel.file_view.dropEvent = self.dropEvent

    def set_move_mode(self):
        self.drag_mode = 'move'
        self.move_btn.setChecked(True)
        self.copy_btn.setChecked(False)

    def set_copy_mode(self):
        self.drag_mode = 'copy'
        self.move_btn.setChecked(False)
        self.copy_btn.setChecked(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            target_panel = self.sender().parent()
            target_path = target_panel.current_path
            for url in event.mimeData().urls():
                src = url.toLocalFile()
                dst = os.path.join(target_path, os.path.basename(src))
                try:
                    if self.drag_mode == 'move':
                        shutil.move(src, dst)
                    else:
                        if os.path.isdir(src):
                            shutil.copytree(src, dst)
                        else:
                            shutil.copy2(src, dst)
                except Exception as e:
                    QMessageBox.warning(self, 'Error', str(e))
            target_panel.model.refresh()
            event.acceptProposedAction()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Backspace:
            focus = QApplication.focusWidget()
            if isinstance(focus, QListView):
                focus.parent().delete_selected()
        else:
            super().keyPressEvent(event)

def main():
    app = QApplication(sys.argv)
    win = FileManager()
    win.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main() 