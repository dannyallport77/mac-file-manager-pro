#!/usr/bin/env python3
"""
MAC File Manager Pro - A professional dual-pane file manager for macOS
"""

import os
import sys
import subprocess
import logging
import threading
import time
import zipfile
import tarfile
import mimetypes
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QListView, QTreeView, QTableView, QHeaderView, QSplitter, QPushButton, QLabel, QComboBox,
    QLineEdit, QSlider, QMenu, QMessageBox, QStyledItemDelegate, QStyle, QSizePolicy,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsProxyWidget, QFrame, QDialog,
    QTextEdit, QPlainTextEdit, QScrollArea, QProgressBar, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt, QSize, QDir, QFileInfo, QAbstractTableModel, QModelIndex, QThread, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, QUrl
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QStandardItemModel, QStandardItem, QFont, QPen, QBrush, QMovie, QTextCursor, QSyntaxHighlighter, QTextCharFormat
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget

# Try to import QWebEngineView, but make it optional
try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView
    WEB_ENGINE_AVAILABLE = True
except ImportError:
    WEB_ENGINE_AVAILABLE = False
    QWebEngineView = None

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VideoPreviewWidget(QWidget):
    """Widget for video preview with play controls"""
    
    def __init__(self, video_path, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.setup_ui()
        self.setup_media_player()
        
    def setup_ui(self):
        """Set up the video preview UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Video widget
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumSize(200, 150)
        layout.addWidget(self.video_widget)
        
        # Play button overlay
        self.play_button = QPushButton("▶")
        self.play_button.setFixedSize(60, 60)
        self.play_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 0, 0, 0.7);
                border-radius: 30px;
                color: white;
                font-size: 24px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.8);
            }
        """)
        self.play_button.clicked.connect(self.toggle_playback)
        
        # Progress slider
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setVisible(False)
        self.progress_slider.sliderMoved.connect(self.seek_video)
        
        # Volume slider
        self.volume_slider = QSlider(Qt.Vertical)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setVisible(False)
        self.volume_slider.valueChanged.connect(self.set_volume)
        
        # Controls layout
        controls_layout = QHBoxLayout()
        controls_layout.addWidget(self.play_button)
        controls_layout.addWidget(self.progress_slider)
        controls_layout.addWidget(self.volume_slider)
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)
        
    def setup_media_player(self):
        """Set up the media player"""
        self.media_player = QMediaPlayer()
        self.media_player.setVideoOutput(self.video_widget)
        self.media_player.setMedia(QMediaContent(QFileInfo(self.video_path).absoluteFilePath()))
        
        # Connect signals
        self.media_player.positionChanged.connect(self.update_progress)
        self.media_player.durationChanged.connect(self.setup_progress_slider)
        self.media_player.stateChanged.connect(self.on_state_changed)
        
        # Set initial volume
        self.media_player.setVolume(50)
        
    def toggle_playback(self):
        """Toggle video play/pause"""
        if self.media_player.state() == QMediaPlayer.PlayingState:
            self.media_player.pause()
        else:
            # Register with global media manager
            global_media_manager.register_media_player(self.media_player)
            self.media_player.play()
            
    def seek_video(self, position):
        """Seek to position in video"""
        self.media_player.setPosition(position)
        
    def set_volume(self, volume):
        """Set video volume"""
        self.media_player.setVolume(volume)
        
    def update_progress(self, position):
        """Update progress slider"""
        if not self.progress_slider.isSliderDown():
            self.progress_slider.setValue(position)
            
    def setup_progress_slider(self, duration):
        """Set up progress slider range"""
        self.progress_slider.setRange(0, duration)
        
    def on_state_changed(self, state):
        """Handle media player state changes"""
        if state == QMediaPlayer.PlayingState:
            self.play_button.setText("⏸")
            self.progress_slider.setVisible(True)
            self.volume_slider.setVisible(True)
        else:
            self.play_button.setText("▶")
            self.progress_slider.setVisible(False)
            self.volume_slider.setVisible(False)
            
    def mousePressEvent(self, event):
        """Handle mouse press for scrubbing"""
        if event.button() == Qt.LeftButton:
            # Calculate position based on mouse Y position for scrubbing
            height = self.height()
            y_pos = event.y()
            if y_pos < height * 0.8:  # Only in video area
                progress = (y_pos / height) * self.media_player.duration()
                self.media_player.setPosition(int(progress))
        super().mousePressEvent(event)
        
    def mouseMoveEvent(self, event):
        """Handle mouse move for scrubbing"""
        if event.buttons() & Qt.LeftButton:
            height = self.height()
            y_pos = event.y()
            if y_pos < height * 0.8:
                progress = (y_pos / height) * self.media_player.duration()
                self.media_player.setPosition(int(progress))
        super().mouseMoveEvent(event)

class AudioPreviewWidget(QWidget):
    """Widget for audio preview with play controls"""
    
    def __init__(self, audio_path, parent=None):
        super().__init__(parent)
        self.audio_path = audio_path
        self.setup_ui()
        self.setup_media_player()
        
    def setup_ui(self):
        """Set up the audio preview UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Audio icon
        self.audio_icon = QLabel("🎵")
        self.audio_icon.setAlignment(Qt.AlignCenter)
        self.audio_icon.setStyleSheet("font-size: 48px;")
        layout.addWidget(self.audio_icon)
        
        # Play button
        self.play_button = QPushButton("▶")
        self.play_button.setFixedSize(50, 50)
        self.play_button.setStyleSheet("""
            QPushButton {
                background-color: #007AFF;
                border-radius: 25px;
                color: white;
                font-size: 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056CC;
            }
        """)
        self.play_button.clicked.connect(self.toggle_playback)
        layout.addWidget(self.play_button, alignment=Qt.AlignCenter)
        
        # Progress slider
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.sliderMoved.connect(self.seek_audio)
        layout.addWidget(self.progress_slider)
        
        # Volume slider
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.valueChanged.connect(self.set_volume)
        layout.addWidget(self.volume_slider)
        
    def setup_media_player(self):
        """Set up the media player"""
        self.media_player = QMediaPlayer()
        self.media_player.setMedia(QMediaContent(QFileInfo(self.audio_path).absoluteFilePath()))
        
        # Connect signals
        self.media_player.positionChanged.connect(self.update_progress)
        self.media_player.durationChanged.connect(self.setup_progress_slider)
        self.media_player.stateChanged.connect(self.on_state_changed)
        
        # Set initial volume
        self.media_player.setVolume(50)
        
    def toggle_playback(self):
        """Toggle audio play/pause"""
        if self.media_player.state() == QMediaPlayer.PlayingState:
            self.media_player.pause()
        else:
            # Register with global media manager
            global_media_manager.register_media_player(self.media_player)
            self.media_player.play()
            
    def seek_audio(self, position):
        """Seek to position in audio"""
        self.media_player.setPosition(position)
        
    def set_volume(self, volume):
        """Set audio volume"""
        self.media_player.setVolume(volume)
        
    def update_progress(self, position):
        """Update progress slider"""
        if not self.progress_slider.isSliderDown():
            self.progress_slider.setValue(position)
            
    def setup_progress_slider(self, duration):
        """Set up progress slider range"""
        self.progress_slider.setRange(0, duration)
        
    def on_state_changed(self, state):
        """Handle media player state changes"""
        if state == QMediaPlayer.PlayingState:
            self.play_button.setText("⏸")
        else:
            self.play_button.setText("▶")

class DocumentPreviewWidget(QWidget):
    """Widget for document preview"""
    
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the document preview UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Document icon based on file type
        file_ext = Path(self.file_path).suffix.lower()
        icon_map = {
            '.pdf': '📄',
            '.doc': '📝', '.docx': '📝',
            '.txt': '📄',
            '.rtf': '📄',
            '.html': '🌐', '.htm': '🌐',
            '.xml': '📄',
            '.json': '📄',
            '.csv': '📊',
            '.xls': '📊', '.xlsx': '📊',
            '.ppt': '📊', '.pptx': '📊'
        }
        
        icon = icon_map.get(file_ext, '📄')
        self.doc_icon = QLabel(icon)
        self.doc_icon.setAlignment(Qt.AlignCenter)
        self.doc_icon.setStyleSheet("font-size: 48px;")
        layout.addWidget(self.doc_icon)
        
        # File name
        self.file_name = QLabel(Path(self.file_path).name)
        self.file_name.setAlignment(Qt.AlignCenter)
        self.file_name.setWordWrap(True)
        layout.addWidget(self.file_name)
        
        # Preview content (simplified - could be enhanced with actual content preview)
        self.preview_label = QLabel("Click to open document")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.preview_label)
        
        # Open button
        self.open_button = QPushButton("Open")
        self.open_button.clicked.connect(self.open_document)
        layout.addWidget(self.open_button)
        
    def open_document(self):
        """Open the document with default application"""
        try:
            if sys.platform == "darwin":  # macOS
                subprocess.run(["open", self.file_path])
            elif sys.platform == "win32":  # Windows
                os.startfile(self.file_path)
            else:  # Linux
                subprocess.run(["xdg-open", self.file_path])
        except Exception as e:
            logger.error(f"Could not open document {self.file_path}: {e}")

class ThumbnailLoader(QThread):
    """Thread for loading thumbnails asynchronously"""
    
    thumbnail_loaded = pyqtSignal(str, QPixmap)  # file_path, thumbnail
    
    def __init__(self, file_path, size=128):
        super().__init__()
        self.file_path = file_path
        self.size = size
        
    def run(self):
        """Load thumbnail in background thread"""
        try:
            import cv2
            import numpy as np
            file_ext = Path(self.file_path).suffix.lower()
            
            # Video files
            video_exts = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v', '.3gp']
            if file_ext in video_exts:
                cap = cv2.VideoCapture(self.file_path)
                found = False
                max_frames = 30  # Scan up to 30 frames
                for i in range(max_frames):
                    ret, frame = cap.read()
                    if not ret:
                        break
                    # Check if frame is not blank (not all black or all white)
                    if np.mean(frame) > 10 and np.std(frame) > 5:
                        # Convert BGR to RGB
                        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        h, w, ch = rgb_frame.shape
                        bytes_per_line = ch * w
                        qimg = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
                        pixmap = QPixmap.fromImage(qimg)
                        scaled_pixmap = pixmap.scaled(
                            self.size, self.size, 
                            Qt.KeepAspectRatio, 
                            Qt.SmoothTransformation
                        )
                        self.thumbnail_loaded.emit(self.file_path, scaled_pixmap)
                        found = True
                        break
                cap.release()
                if found:
                    return
                # If no good frame found, fall back to default icon
            
            # Image files
            if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']:
                pixmap = QPixmap(self.file_path)
                if not pixmap.isNull():
                    # Scale to thumbnail size
                    scaled_pixmap = pixmap.scaled(
                        self.size, self.size, 
                        Qt.KeepAspectRatio, 
                        Qt.SmoothTransformation
                    )
                    self.thumbnail_loaded.emit(self.file_path, scaled_pixmap)
                    return
                    
            # For other files, use default icon
            default_icon = QPixmap(self.size, self.size)
            default_icon.fill(Qt.lightGray)
            painter = QPainter(default_icon)
            painter.setPen(QPen(Qt.black, 2))
            painter.drawRect(10, 10, self.size - 20, self.size - 20)
            painter.drawText(default_icon.rect(), Qt.AlignCenter, "📄")
            painter.end()
            self.thumbnail_loaded.emit(self.file_path, default_icon)
            
        except Exception as e:
            logger.error(f"Error loading thumbnail for {self.file_path}: {e}")
            # Return default icon on error
            default_icon = QPixmap(self.size, self.size)
            default_icon.fill(Qt.lightGray)
            self.thumbnail_loaded.emit(self.file_path, default_icon)

class TextPreviewWidget(QWidget):
    """Widget for text file preview with syntax highlighting"""
    
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.setup_ui()
        self.load_content()
        
    def setup_ui(self):
        """Set up the text preview UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # File name header
        self.file_name = QLabel(Path(self.file_path).name)
        self.file_name.setStyleSheet("font-weight: bold; font-size: 12px; padding: 5px;")
        layout.addWidget(self.file_name)
        
        # Text editor
        self.text_edit = QPlainTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setMaximumHeight(200)
        self.text_edit.setStyleSheet("""
            QPlainTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
                font-size: 10px;
            }
        """)
        layout.addWidget(self.text_edit)
        
        # Open button
        self.open_button = QPushButton("Open in Editor")
        self.open_button.clicked.connect(self.open_in_editor)
        layout.addWidget(self.open_button)
        
    def load_content(self):
        """Load file content"""
        try:
            with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                # Show first 1000 characters
                preview_content = content[:1000]
                if len(content) > 1000:
                    preview_content += "\n\n... (truncated)"
                self.text_edit.setPlainText(preview_content)
        except Exception as e:
            self.text_edit.setPlainText(f"Error loading file: {e}")
            
    def open_in_editor(self):
        """Open file in default text editor"""
        try:
            if sys.platform == "darwin":  # macOS
                subprocess.run(["open", "-t", self.file_path])
            elif sys.platform == "win32":  # Windows
                subprocess.run(["notepad", self.file_path])
            else:  # Linux
                subprocess.run(["xdg-open", self.file_path])
        except Exception as e:
            logger.error(f"Could not open file {self.file_path}: {e}")

class ArchivePreviewWidget(QWidget):
    """Widget for archive file preview"""
    
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.setup_ui()
        self.load_contents()
        
    def setup_ui(self):
        """Set up the archive preview UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # File name header
        self.file_name = QLabel(Path(self.file_path).name)
        self.file_name.setStyleSheet("font-weight: bold; font-size: 12px; padding: 5px;")
        layout.addWidget(self.file_name)
        
        # Archive icon
        self.archive_icon = QLabel("📦")
        self.archive_icon.setAlignment(Qt.AlignCenter)
        self.archive_icon.setStyleSheet("font-size: 32px;")
        layout.addWidget(self.archive_icon)
        
        # Contents list
        self.contents_list = QListWidget()
        self.contents_list.setMaximumHeight(150)
        layout.addWidget(self.contents_list)
        
        # Extract button
        self.extract_button = QPushButton("Extract")
        self.extract_button.clicked.connect(self.extract_archive)
        layout.addWidget(self.extract_button)
        
    def load_contents(self):
        """Load archive contents"""
        try:
            file_ext = Path(self.file_path).suffix.lower()
            
            if file_ext == '.zip':
                with zipfile.ZipFile(self.file_path, 'r') as zip_file:
                    file_list = zip_file.namelist()
            elif file_ext in ['.tar', '.tar.gz', '.tgz']:
                with tarfile.open(self.file_path, 'r:*') as tar_file:
                    file_list = tar_file.getnames()
            else:
                self.contents_list.addItem("Unsupported archive format")
                return
                
            # Add first 20 files to list
            for i, file_name in enumerate(file_list[:20]):
                item = QListWidgetItem(file_name)
                self.contents_list.addItem(item)
                
            if len(file_list) > 20:
                self.contents_list.addItem(f"... and {len(file_list) - 20} more files")
                
        except Exception as e:
            self.contents_list.addItem(f"Error reading archive: {e}")
            
    def extract_archive(self):
        """Extract archive to current directory"""
        try:
            extract_dir = str(Path(self.file_path).parent)
            file_ext = Path(self.file_path).suffix.lower()
            
            if file_ext == '.zip':
                with zipfile.ZipFile(self.file_path, 'r') as zip_file:
                    zip_file.extractall(extract_dir)
            elif file_ext in ['.tar', '.tar.gz', '.tgz']:
                with tarfile.open(self.file_path, 'r:*') as tar_file:
                    tar_file.extractall(extract_dir)
                    
            QMessageBox.information(self, "Extract Complete", f"Archive extracted to {extract_dir}")
            
        except Exception as e:
            QMessageBox.critical(self, "Extract Error", f"Could not extract archive: {e}")

class HTMLPreviewWidget(QWidget):
    """Widget for HTML file preview"""
    
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the HTML preview UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # File name header
        self.file_name = QLabel(Path(self.file_path).name)
        self.file_name.setStyleSheet("font-weight: bold; font-size: 12px; padding: 5px;")
        layout.addWidget(self.file_name)
        
        if WEB_ENGINE_AVAILABLE and QWebEngineView:
            # Web view for HTML preview
            self.web_view = QWebEngineView()
            self.web_view.setMaximumHeight(200)
            self.web_view.load(QUrl.fromLocalFile(self.file_path))
            layout.addWidget(self.web_view)
        else:
            # Fallback if QWebEngineView is not available
            self.fallback_label = QLabel("HTML Preview not available (QWebEngineView not installed)")
            self.fallback_label.setAlignment(Qt.AlignCenter)
            self.fallback_label.setStyleSheet("color: #666; font-style: italic;")
            layout.addWidget(self.fallback_label)
        
        # Open button
        self.open_button = QPushButton("Open in Browser")
        self.open_button.clicked.connect(self.open_in_browser)
        layout.addWidget(self.open_button)
        
    def open_in_browser(self):
        """Open HTML file in default browser"""
        try:
            if sys.platform == "darwin":  # macOS
                subprocess.run(["open", self.file_path])
            elif sys.platform == "win32":  # Windows
                subprocess.run(["start", self.file_path], shell=True)
            else:  # Linux
                subprocess.run(["xdg-open", self.file_path])
        except Exception as e:
            logger.error(f"Could not open HTML file {self.file_path}: {e}")

class GIFPreviewWidget(QWidget):
    """Widget for GIF preview with animation controls"""
    
    def __init__(self, gif_path, parent=None):
        super().__init__(parent)
        self.gif_path = gif_path
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the GIF preview UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # GIF label
        self.gif_label = QLabel()
        self.gif_label.setAlignment(Qt.AlignCenter)
        self.gif_label.setMinimumSize(200, 150)
        self.gif_label.setMaximumSize(300, 200)
        layout.addWidget(self.gif_label)
        
        # Load and start GIF animation
        self.movie = QMovie(self.gif_path)
        self.movie.setCacheMode(QMovie.CacheAll)
        self.gif_label.setMovie(self.movie)
        self.movie.start()
        
        # Controls
        controls_layout = QHBoxLayout()
        
        self.play_button = QPushButton("⏸")
        self.play_button.setFixedSize(40, 30)
        self.play_button.clicked.connect(self.toggle_animation)
        controls_layout.addWidget(self.play_button)
        
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(50, 200)
        self.speed_slider.setValue(100)
        self.speed_slider.setToolTip("Animation Speed")
        self.speed_slider.valueChanged.connect(self.set_speed)
        controls_layout.addWidget(self.speed_slider)
        
        layout.addLayout(controls_layout)
        
    def toggle_animation(self):
        """Toggle GIF animation play/pause"""
        if self.movie.state() == QMovie.Running:
            self.movie.setPaused(True)
            self.play_button.setText("▶")
        else:
            # Register with global media manager
            global_media_manager.register_gif_movie(self.movie)
            self.movie.setPaused(False)
            self.play_button.setText("⏸")
            
    def set_speed(self, speed):
        """Set animation speed (50-200%)"""
        self.movie.setSpeed(speed)

class FileTableModel(QAbstractTableModel):
    """Custom table model for file/folder data with multiple columns"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = []
        self._headers = ['Name', 'Size', 'Type', 'Date Modified']
        self._visible_columns = [0, 1, 2, 3]  # All columns visible by default
        
    def rowCount(self, parent=QModelIndex()):
        return len(self._data)
    
    def columnCount(self, parent=QModelIndex()):
        return len(self._visible_columns)
    
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
            
        if role == Qt.DisplayRole:
            row = index.row()
            col = self._visible_columns[index.column()]
            if row < len(self._data) and col < len(self._data[row]):
                return self._data[row][col]
        elif role == Qt.DecorationRole and index.column() == 0:
            # Icon for the first column (Name)
            row = index.row()
            if row < len(self._data) and len(self._data[row]) > 4:
                return self._data[row][4]  # Icon is stored at index 4
        elif role == Qt.UserRole:
            # Return the full file path
            row = index.row()
            if row < len(self._data) and len(self._data[row]) > 5:
                return self._data[row][5]  # File path is stored at index 5
                
        return None
    
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section < len(self._visible_columns):
                return self._headers[self._visible_columns[section]]
        return None
    
    def setData(self, data_list):
        """Set the data for the model"""
        self.beginResetModel()
        self._data = data_list
        self.endResetModel()
    
    def getVisibleColumns(self):
        """Get list of visible column indices"""
        return self._visible_columns.copy()
    
    def setVisibleColumns(self, columns):
        """Set which columns are visible"""
        self.beginResetModel()
        self._visible_columns = columns
        self.endResetModel()
    
    def getColumnName(self, column_index):
        """Get the name of a column by its index"""
        if column_index < len(self._headers):
            return self._headers[column_index]
        return ""
    
    def getAllColumns(self):
        """Get all available column names"""
        return self._headers.copy()
    
    def sort(self, column, order):
        """Sort the data by column"""
        if column >= len(self._visible_columns):
            return
            
        actual_column = self._visible_columns[column]
        
        # Sort the data
        reverse = (order == Qt.DescendingOrder)
        
        if actual_column == 0:  # Name column
            self._data.sort(key=lambda x: x[0].lower(), reverse=reverse)
        elif actual_column == 1:  # Size column
            self._data.sort(key=lambda x: self._parse_size(x[1]), reverse=reverse)
        elif actual_column == 2:  # Type column
            self._data.sort(key=lambda x: x[2].lower(), reverse=reverse)
        elif actual_column == 3:  # Date column
            self._data.sort(key=lambda x: x[3], reverse=reverse)
        
        self.layoutChanged.emit()
    
    def _parse_size(self, size_str):
        """Parse size string to numeric value for sorting"""
        if size_str == "<DIR>":
            return -1  # Folders come first
        
        try:
            # Remove unit and convert to bytes
            size_str = size_str.strip()
            if size_str.endswith(" B"):
                return float(size_str[:-2])
            elif size_str.endswith(" KB"):
                return float(size_str[:-3]) * 1024
            elif size_str.endswith(" MB"):
                return float(size_str[:-3]) * 1024 * 1024
            elif size_str.endswith(" GB"):
                return float(size_str[:-3]) * 1024 * 1024 * 1024
            elif size_str.endswith(" TB"):
                return float(size_str[:-3]) * 1024 * 1024 * 1024 * 1024
            else:
                return float(size_str)
        except:
            return 0

class GlobalMediaManager:
    """Global manager to ensure only one media file plays at a time"""
    
    def __init__(self):
        self.current_media_player = None
        self.current_gif_movie = None
        
    def stop_current_media(self):
        """Stop any currently playing media"""
        if self.current_media_player:
            self.current_media_player.stop()
            self.current_media_player = None
            
        if self.current_gif_movie:
            self.current_gif_movie.setPaused(True)
            self.current_gif_movie = None
            
    def register_media_player(self, media_player):
        """Register a new media player and stop others"""
        self.stop_current_media()
        self.current_media_player = media_player
        
    def register_gif_movie(self, movie):
        """Register a new GIF movie and stop others"""
        self.stop_current_media()
        self.current_gif_movie = movie

# Global media manager instance
global_media_manager = GlobalMediaManager()

class FileManager(QMainWindow):
    """Dual-pane file manager with independent navigation"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("MAC File Manager Pro")
        self.setGeometry(100, 100, 1600, 800)
        
        # Initialize current directories for both panes
        self.left_current_directory = QDir.homePath()
        self.right_current_directory = QDir.homePath()
        
        # Initialize current view modes
        self.left_current_view_mode = 'icon'
        self.right_current_view_mode = 'icon'
        
        # Create models for both panes
        self.left_folder_model = QStandardItemModel()
        self.left_file_model = QStandardItemModel()
        self.right_folder_model = QStandardItemModel()
        self.right_file_model = QStandardItemModel()
        
        # Create table models for column view
        self.left_folder_table_model = FileTableModel()
        self.left_file_table_model = FileTableModel()
        self.right_folder_table_model = FileTableModel()
        self.right_file_table_model = FileTableModel()
        
        # Thumbnail cache
        self.thumbnail_cache = {}
        self.thumbnail_loaders = {}
        
        # In-place preview tracking
        self.left_preview_widget = None
        self.right_preview_widget = None
        self.left_preview_item = None
        self.right_preview_item = None
        
        # Set up views
        self.setup_views()
        
        # Create dual-pane layout
        self.create_dual_pane_layout()
        
        # Set up context menus
        self.setup_context_menus()
        
        # Load initial directories
        self.load_left_directory(self.left_current_directory)
        self.load_right_directory(self.right_current_directory)
        
        # Update folder selectors with initial paths
        if hasattr(self, 'left_folder_selector'):
            self.left_folder_selector.setCurrentText(self.left_current_directory)
        if hasattr(self, 'right_folder_selector'):
            self.right_folder_selector.setCurrentText(self.right_current_directory)
    
    def setup_views(self):
        """Set up all views for both panes"""
        # Left pane views
        self.left_folder_view = QListView()
        self.left_file_view = QListView()
        
        self.left_folder_view.setModel(self.left_folder_model)
        self.left_file_view.setModel(self.left_file_model)
        
        # Right pane views
        self.right_folder_view = QListView()
        self.right_file_view = QListView()
        
        self.right_folder_view.setModel(self.right_folder_model)
        self.right_file_view.setModel(self.right_file_model)
        
        # Set up view properties
        for view in [self.left_folder_view, self.left_file_view, 
                    self.right_folder_view, self.right_file_view]:
            view.setViewMode(QListView.IconMode)
            view.setIconSize(QSize(32, 32))
            view.setResizeMode(QListView.Adjust)
            view.setMinimumWidth(200)
            view.setMinimumHeight(120)
            # Configure for consistent grid layout
            view.setGridSize(QSize(80, 80))  # Fixed grid size for consistent spacing
            view.setSpacing(4)  # Small spacing between items
            view.setWordWrap(True)  # Enable text wrapping
            view.setTextElideMode(Qt.ElideMiddle)  # Truncate long text with "..."
            view.setUniformItemSizes(False)  # Allow different text lengths
        
        # Connect signals
        self.left_folder_view.clicked.connect(self.on_left_folder_clicked)
        self.left_file_view.clicked.connect(self.on_left_file_clicked)
        self.left_file_view.doubleClicked.connect(self.on_left_file_double_clicked)
        self.right_folder_view.clicked.connect(self.on_right_folder_clicked)
        self.right_file_view.clicked.connect(self.on_right_file_clicked)
        self.right_file_view.doubleClicked.connect(self.on_right_file_double_clicked)
    
    def create_dual_pane_layout(self):
        """Create the dual-pane layout with toolbars"""
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create left pane with toolbar
        left_pane = self.create_pane_with_toolbar("Left", self.left_folder_view, self.left_file_view)
        
        # Create right pane with toolbar
        right_pane = self.create_pane_with_toolbar("Right", self.right_folder_view, self.right_file_view)
        
        # Create horizontal splitter for dual-pane
        self.dual_splitter = QSplitter(Qt.Horizontal)
        self.dual_splitter.addWidget(left_pane)
        self.dual_splitter.addWidget(right_pane)
        self.dual_splitter.setSizes([800, 800])
        
        main_layout.addWidget(self.dual_splitter)
        self.setCentralWidget(central_widget)
    
    def create_pane_with_toolbar(self, pane_name, folder_view, file_view):
        """Create a pane with its own toolbar and folder/file split"""
        pane_widget = QWidget()
        pane_layout = QHBoxLayout(pane_widget)
        pane_layout.setContentsMargins(2, 2, 2, 2)
        pane_layout.setSpacing(2)

        # View mode buttons as a vertical bar
        view_mode_bar = self.create_view_mode_bar(pane_name)
        if pane_name == "Left":
            pane_layout.addLayout(view_mode_bar)
        
        # Main vertical layout for toolbar, filter, and views
        main_vbox = QVBoxLayout()
        main_vbox.setContentsMargins(0, 0, 0, 0)
        main_vbox.setSpacing(2)

        # Create toolbar for this pane
        toolbar = self.create_pane_toolbar(pane_name)
        main_vbox.addLayout(toolbar)

        # Create filter toolbar for this pane
        filter_toolbar = self.create_pane_filter_toolbar(pane_name)
        main_vbox.addLayout(filter_toolbar)

        # Create vertical splitter for folder (top) and file (bottom) views
        pane_splitter = QSplitter(Qt.Vertical)
        pane_splitter.addWidget(folder_view)
        pane_splitter.addWidget(file_view)
        pane_splitter.setSizes([150, 300])

        main_vbox.addWidget(pane_splitter)
        pane_layout.addLayout(main_vbox)

        if pane_name == "Right":
            pane_layout.addLayout(view_mode_bar)

        return pane_widget

    def create_view_mode_bar(self, pane_name):
        """Create a vertical bar of view mode buttons for a specific pane, including the size slider at the bottom"""
        bar = QVBoxLayout()
        bar.setContentsMargins(0, 0, 0, 0)
        bar.setSpacing(6)
        bar.addStretch()
        icon_btn = QPushButton("📁")
        icon_btn.setCheckable(True)
        icon_btn.setToolTip(f"Icon view in {pane_name} pane")
        icon_btn.clicked.connect(lambda: self.set_view_mode(pane_name, 'icon'))
        column_btn = QPushButton("📊")
        column_btn.setCheckable(True)
        column_btn.setToolTip(f"Column view in {pane_name} pane")
        column_btn.clicked.connect(lambda: self.set_view_mode(pane_name, 'column'))
        thumbnail_btn = QPushButton("🖼️")
        thumbnail_btn.setCheckable(True)
        thumbnail_btn.setToolTip(f"Thumbnail view in {pane_name} pane")
        thumbnail_btn.clicked.connect(lambda: self.set_view_mode(pane_name, 'thumbnail'))
        for btn in [icon_btn, column_btn, thumbnail_btn]:
            btn.setMaximumWidth(40)
            btn.setMinimumHeight(40)
            bar.addWidget(btn)
        bar.addSpacing(12)
        # Size slider and label at the bottom
        size_label = QLabel("Size")
        size_label.setAlignment(Qt.AlignHCenter)
        bar.addWidget(size_label)
        size_slider = QSlider(Qt.Vertical)
        size_slider.setRange(24, 96)
        size_slider.setValue(32)
        size_slider.setMinimumHeight(100)
        size_slider.setMaximumHeight(120)
        size_slider.setTickPosition(QSlider.TicksBothSides)
        size_slider.setTickInterval(8)
        size_slider.valueChanged.connect(lambda value: self.set_icon_size(pane_name, value))
        bar.addWidget(size_slider)
        bar.addStretch()
        # Store references for exclusive selection and slider
        if pane_name == "Left":
            self.left_view_buttons = [icon_btn, column_btn, thumbnail_btn]
            self.left_size_slider = size_slider
        else:
            self.right_view_buttons = [icon_btn, column_btn, thumbnail_btn]
            self.right_size_slider = size_slider
        return bar
    
    def create_pane_toolbar(self, pane_name):
        """Create toolbar for a specific pane"""
        toolbar = QHBoxLayout()
        toolbar.setSpacing(4)
        
        # Navigation buttons (compact)
        back_btn = QPushButton("←")
        back_btn.setMaximumWidth(40)
        back_btn.setMinimumHeight(25)
        back_btn.setToolTip(f"Go back in {pane_name} pane")
        back_btn.clicked.connect(lambda: self.go_back(pane_name))
        toolbar.addWidget(back_btn)
        
        forward_btn = QPushButton("→")
        forward_btn.setMaximumWidth(40)
        forward_btn.setMinimumHeight(25)
        forward_btn.setToolTip(f"Go forward in {pane_name} pane")
        forward_btn.clicked.connect(lambda: self.go_forward(pane_name))
        toolbar.addWidget(forward_btn)
        
        up_btn = QPushButton("↑")
        up_btn.setMaximumWidth(40)
        up_btn.setMinimumHeight(25)
        up_btn.setToolTip(f"Go up in {pane_name} pane")
        up_btn.clicked.connect(lambda: self.go_up(pane_name))
        toolbar.addWidget(up_btn)
        
        # Path label to the left of the dropdown
        path_label = QLabel("Path:")
        path_label.setMinimumHeight(25)
        toolbar.addWidget(path_label)
        
        # Folder selector dropdown with expanding width
        folder_selector = QComboBox()
        folder_selector.setEditable(True)
        folder_selector.setMinimumWidth(200)
        folder_selector.setMinimumHeight(25)
        folder_selector.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        folder_selector.setToolTip(f"Current folder path in {pane_name} pane")
        folder_selector.currentTextChanged.connect(lambda text: self.on_folder_selector_changed(pane_name, text))
        toolbar.addWidget(folder_selector)
        
        # Bookmark button
        bookmark_btn = QPushButton("★")
        bookmark_btn.setMaximumWidth(40)
        bookmark_btn.setMinimumHeight(25)
        bookmark_btn.setToolTip(f"Add current folder to bookmarks in {pane_name} pane")
        bookmark_btn.clicked.connect(lambda: self.add_bookmark(pane_name))
        toolbar.addWidget(bookmark_btn)
        
        # Store references for later use
        if pane_name == "Left":
            self.left_back_btn = back_btn
            self.left_forward_btn = forward_btn
            self.left_up_btn = up_btn
            self.left_folder_selector = folder_selector
            self.left_bookmark_btn = bookmark_btn
        else:
            self.right_back_btn = back_btn
            self.right_forward_btn = forward_btn
            self.right_up_btn = up_btn
            self.right_folder_selector = folder_selector
            self.right_bookmark_btn = bookmark_btn
        
        return toolbar
    
    def create_pane_filter_toolbar(self, pane_name):
        """Create filter toolbar for a specific pane"""
        filter_toolbar = QHBoxLayout()
        filter_toolbar.setSpacing(4)
        
        # Search box
        filter_toolbar.addWidget(QLabel("Search:"))
        search_box = QLineEdit()
        search_box.setPlaceholderText("Search folders and files...")
        search_box.setMinimumWidth(150)
        search_box.setMaximumWidth(200)
        search_box.setMinimumHeight(25)
        search_box.textChanged.connect(lambda text: self.on_search_text_changed(pane_name, text))
        filter_toolbar.addWidget(search_box)
        
        # Sort dropdown
        filter_toolbar.addWidget(QLabel("Sort:"))
        sort_combo = QComboBox()
        sort_combo.addItems(['Name', 'Size', 'Type', 'Date'])
        sort_combo.setMaximumWidth(80)
        sort_combo.setMinimumHeight(25)
        sort_combo.currentTextChanged.connect(lambda text: self.on_sort_changed(pane_name, text))
        filter_toolbar.addWidget(sort_combo)
        
        filter_toolbar.addStretch()
        
        # Store references for later use
        if pane_name == "Left":
            self.left_search_box = search_box
            self.left_sort_combo = sort_combo
        else:
            self.right_search_box = search_box
            self.right_sort_combo = sort_combo
        
        return filter_toolbar
    
    def load_left_directory(self, path):
        """Load directory into left pane"""
        if not os.path.isdir(path):
            return
        
        self.left_current_directory = path
        self.load_folders_to_model(self.left_folder_model, path)
        self.load_files_to_model(self.left_file_model, path)
        # Also load into table models for column view
        self.load_folders_to_table_model(self.left_folder_table_model, path)
        self.load_files_to_table_model(self.left_file_table_model, path)
        # Update the folder selector dropdown
        if hasattr(self, 'left_folder_selector'):
            self.left_folder_selector.setCurrentText(path)
    
    def load_right_directory(self, path):
        """Load directory into right pane"""
        if not os.path.isdir(path):
            return
        
        self.right_current_directory = path
        self.load_folders_to_model(self.right_folder_model, path)
        self.load_files_to_model(self.right_file_model, path)
        # Also load into table models for column view
        self.load_folders_to_table_model(self.right_folder_table_model, path)
        self.load_files_to_table_model(self.right_file_table_model, path)
        # Update the folder selector dropdown
        if hasattr(self, 'right_folder_selector'):
            self.right_folder_selector.setCurrentText(path)
    
    def load_folders_to_model(self, model, path):
        """Load folders into a model"""
        model.clear()
        
        try:
            dir_info = QDir(path)
            dir_info.setFilter(QDir.Dirs | QDir.NoDotAndDotDot)
            entries = dir_info.entryInfoList()
            
            for entry in entries:
                item = QStandardItem(entry.fileName())
                item.setData(entry.filePath(), Qt.UserRole)
                item.setIcon(self.style().standardIcon(QStyle.SP_DirIcon))
                model.appendRow(item)
                
        except Exception as e:
            logger.error(f"Error loading folders from {path}: {e}")
    
    def load_folders_to_table_model(self, table_model, path):
        """Load folders into a table model with multiple columns"""
        table_data = []
        
        try:
            dir_info = QDir(path)
            dir_info.setFilter(QDir.Dirs | QDir.NoDotAndDotDot)
            entries = dir_info.entryInfoList()
            
            for entry in entries:
                # Get folder info
                name = entry.fileName()
                size = "<DIR>"  # Folders don't have size in traditional sense
                file_type = "Folder"
                date_modified = entry.lastModified().toString("MMM dd, yyyy hh:mm")
                icon = self.style().standardIcon(QStyle.SP_DirIcon)
                file_path = entry.filePath()
                
                # Add to table data: [Name, Size, Type, Date Modified, Icon, FilePath]
                table_data.append([name, size, file_type, date_modified, icon, file_path])
                
        except Exception as e:
            logger.error(f"Error loading folders to table model from {path}: {e}")
        
        table_model.setData(table_data)
    
    def load_files_to_model(self, model, path):
        """Load files into a model"""
        model.clear()
        
        try:
            dir_info = QDir(path)
            dir_info.setFilter(QDir.Files | QDir.NoDotAndDotDot)
            entries = dir_info.entryInfoList()
            
            for entry in entries:
                item = QStandardItem(entry.fileName())
                item.setData(entry.filePath(), Qt.UserRole)
                
                # Set default icon first
                item.setIcon(self.style().standardIcon(QStyle.SP_FileIcon))
                
                # Load thumbnail if in thumbnail mode
                if hasattr(self, 'left_current_view_mode') and self.left_current_view_mode == 'thumbnail':
                    self.load_thumbnail(entry.filePath(), item)
                
                model.appendRow(item)
                
        except Exception as e:
            logger.error(f"Error loading files from {path}: {e}")
    
    def load_files_to_table_model(self, table_model, path):
        """Load files into a table model with multiple columns"""
        table_data = []
        
        try:
            dir_info = QDir(path)
            dir_info.setFilter(QDir.Files | QDir.NoDotAndDotDot)
            entries = dir_info.entryInfoList()
            
            for entry in entries:
                # Get file info
                name = entry.fileName()
                size = self.format_file_size(entry.size())
                file_type = self.get_file_type(entry.fileName())
                date_modified = entry.lastModified().toString("MMM dd, yyyy hh:mm")
                icon = self.style().standardIcon(QStyle.SP_FileIcon)
                file_path = entry.filePath()
                
                # Add to table data: [Name, Size, Type, Date Modified, Icon, FilePath]
                table_data.append([name, size, file_type, date_modified, icon, file_path])
                
        except Exception as e:
            logger.error(f"Error loading files to table model from {path}: {e}")
        
        table_model.setData(table_data)
    
    def format_file_size(self, size_bytes):
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"
    
    def get_file_type(self, filename):
        """Get file type based on extension"""
        if '.' in filename:
            ext = filename.split('.')[-1].lower()
            return f"{ext.upper()} File"
        return "File"
    
    def get_file_category(self, file_path):
        """Get file category for preview/thumbnail purposes"""
        file_ext = Path(file_path).suffix.lower()
        
        # Video files
        video_exts = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v', '.3gp']
        if file_ext in video_exts:
            return 'video'
            
        # Audio files
        audio_exts = ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma', '.aiff']
        if file_ext in audio_exts:
            return 'audio'
            
        # GIF files (special handling for animation)
        if file_ext == '.gif':
            return 'gif'
            
        # Image files
        image_exts = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp', '.svg']
        if file_ext in image_exts:
            return 'image'
            
        # Text files
        text_exts = ['.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml', '.csv', '.log', '.ini', '.cfg', '.conf']
        if file_ext in text_exts:
            return 'text'
            
        # Archive files
        archive_exts = ['.zip', '.tar', '.tar.gz', '.tgz', '.rar', '.7z']
        if file_ext in archive_exts:
            return 'archive'
            
        # HTML files
        if file_ext in ['.html', '.htm']:
            return 'html'
            
        # Document files
        doc_exts = ['.pdf', '.doc', '.docx', '.rtf', '.xls', '.xlsx', '.ppt', '.pptx']
        if file_ext in doc_exts:
            return 'document'
            
        return 'other'
    
    def create_preview_widget(self, file_path):
        """Create appropriate preview widget for file type"""
        category = self.get_file_category(file_path)
        
        if category == 'video':
            return VideoPreviewWidget(file_path)
        elif category == 'audio':
            return AudioPreviewWidget(file_path)
        elif category == 'gif':
            return GIFPreviewWidget(file_path)
        elif category == 'text':
            return TextPreviewWidget(file_path)
        elif category == 'archive':
            return ArchivePreviewWidget(file_path)
        elif category == 'html':
            return HTMLPreviewWidget(file_path)
        elif category == 'document':
            return DocumentPreviewWidget(file_path)
        else:
            # For other files, return None to use default icon
            return None
    
    def load_thumbnail(self, file_path, item):
        """Load thumbnail for a file"""
        # Check cache first
        if file_path in self.thumbnail_cache:
            item.setIcon(QIcon(self.thumbnail_cache[file_path]))
            return
            
        # Don't load thumbnails for folders
        if os.path.isdir(file_path):
            return
            
        # Start thumbnail loading in background
        loader = ThumbnailLoader(file_path, 128)
        loader.thumbnail_loaded.connect(lambda path, pixmap: self.on_thumbnail_loaded(path, pixmap))
        self.thumbnail_loaders[file_path] = loader
        loader.start()
    
    def on_thumbnail_loaded(self, file_path, pixmap):
        """Handle thumbnail loaded signal"""
        # Cache the thumbnail
        self.thumbnail_cache[file_path] = pixmap
        
        # Find and update the item in all models
        self.update_item_icon(file_path, pixmap)
        
        # Clean up loader
        if file_path in self.thumbnail_loaders:
            self.thumbnail_loaders[file_path].deleteLater()
            del self.thumbnail_loaders[file_path]
    
    def update_item_icon(self, file_path, pixmap):
        """Update icon for an item in all models"""
        # Update left file model
        for row in range(self.left_file_model.rowCount()):
            item = self.left_file_model.item(row)
            if item and item.data(Qt.UserRole) == file_path:
                item.setIcon(QIcon(pixmap))
                break
                
        # Update right file model
        for row in range(self.right_file_model.rowCount()):
            item = self.right_file_model.item(row)
            if item and item.data(Qt.UserRole) == file_path:
                item.setIcon(QIcon(pixmap))
                break
    
    def show_in_place_preview(self, pane_name, file_path, item):
        """Show in-place preview for a file"""
        # Hide existing preview in this pane
        self.hide_in_place_preview(pane_name)
        
        # Create preview widget
        preview_widget = self.create_preview_widget(file_path)
        if not preview_widget:
            return
            
        # Store preview widget and item
        if pane_name == "Left":
            self.left_preview_widget = preview_widget
            self.left_preview_item = item
        else:
            self.right_preview_widget = preview_widget
            self.right_preview_item = item
            
        # Replace the item's icon with the preview widget
        # This is a simplified approach - in a real implementation,
        # you'd need to create a custom delegate to embed widgets
        # For now, we'll show the preview in a dialog
        self.show_file_preview(file_path)
    
    def hide_in_place_preview(self, pane_name):
        """Hide in-place preview for a pane"""
        if pane_name == "Left":
            if self.left_preview_widget:
                self.left_preview_widget.deleteLater()
                self.left_preview_widget = None
                self.left_preview_item = None
        else:
            if self.right_preview_widget:
                self.right_preview_widget.deleteLater()
                self.right_preview_widget = None
                self.right_preview_item = None
    
    def on_left_folder_clicked(self, index):
        """Handle left pane folder click"""
        # Handle both standard model and table model
        sender = self.sender()
        if isinstance(sender, QTableView):
            # Table view - get data from table model
            model = sender.model()
            if isinstance(model, FileTableModel):
                file_path = model.data(index, Qt.UserRole)
                if file_path:
                    self.load_left_directory(file_path)
        else:
            # List view - get data from standard model
            item = self.left_folder_model.itemFromIndex(index)
            if item:
                folder_path = item.data(Qt.UserRole)
                self.load_left_directory(folder_path)
    
    def on_left_file_clicked(self, index):
        """Handle left pane file click"""
        # Handle both standard model and table model
        sender = self.sender()
        if isinstance(sender, QTableView):
            # Table view - get data from table model
            model = sender.model()
            if isinstance(model, FileTableModel):
                file_path = model.data(index, Qt.UserRole)
                if file_path:
                    # Show in-place preview
                    item = self.left_file_model.itemFromIndex(index)
                    if item:
                        self.show_in_place_preview("Left", file_path, item)
        else:
            # List view - get data from standard model
            item = self.left_file_model.itemFromIndex(index)
            if item:
                file_path = item.data(Qt.UserRole)
                # Show in-place preview
                self.show_in_place_preview("Left", file_path, item)
    
    def on_left_file_double_clicked(self, index):
        """Handle left pane file double click for opening"""
        sender = self.sender()
        if isinstance(sender, QTableView):
            model = sender.model()
            if isinstance(model, FileTableModel):
                file_path = model.data(index, Qt.UserRole)
                if file_path:
                    self.open_file(file_path)
        else:
            item = self.left_file_model.itemFromIndex(index)
            if item:
                file_path = item.data(Qt.UserRole)
                self.open_file(file_path)
    
    def on_right_folder_clicked(self, index):
        """Handle right pane folder click"""
        # Handle both standard model and table model
        sender = self.sender()
        if isinstance(sender, QTableView):
            # Table view - get data from table model
            model = sender.model()
            if isinstance(model, FileTableModel):
                file_path = model.data(index, Qt.UserRole)
                if file_path:
                    self.load_right_directory(file_path)
        else:
            # List view - get data from standard model
            item = self.right_folder_model.itemFromIndex(index)
            if item:
                folder_path = item.data(Qt.UserRole)
                self.load_right_directory(folder_path)
    
    def on_right_file_clicked(self, index):
        """Handle right pane file click"""
        # Handle both standard model and table model
        sender = self.sender()
        if isinstance(sender, QTableView):
            # Table view - get data from table model
            model = sender.model()
            if isinstance(model, FileTableModel):
                file_path = model.data(index, Qt.UserRole)
                if file_path:
                    # Show in-place preview
                    item = self.right_file_model.itemFromIndex(index)
                    if item:
                        self.show_in_place_preview("Right", file_path, item)
        else:
            # List view - get data from standard model
            item = self.right_file_model.itemFromIndex(index)
            if item:
                file_path = item.data(Qt.UserRole)
                # Show in-place preview
                self.show_in_place_preview("Right", file_path, item)
    
    def on_right_file_double_clicked(self, index):
        """Handle right pane file double click for opening"""
        sender = self.sender()
        if isinstance(sender, QTableView):
            model = sender.model()
            if isinstance(model, FileTableModel):
                file_path = model.data(index, Qt.UserRole)
                if file_path:
                    self.open_file(file_path)
        else:
            item = self.right_file_model.itemFromIndex(index)
            if item:
                file_path = item.data(Qt.UserRole)
                self.open_file(file_path)
    
    def open_file(self, file_path):
        """Open a file with the default application"""
        try:
            if sys.platform == "darwin":  # macOS
                subprocess.run(["open", file_path])
            elif sys.platform == "win32":  # Windows
                os.startfile(file_path)
            else:  # Linux
                subprocess.run(["xdg-open", file_path])
        except Exception as e:
            logger.error(f"Could not open file {file_path}: {e}")
    
    def show_file_preview(self, file_path):
        """Show file preview in a dialog"""
        category = self.get_file_category(file_path)
        
        if category in ['video', 'audio', 'document']:
            preview_widget = self.create_preview_widget(file_path)
            if preview_widget:
                dialog = QDialog(self)
                dialog.setWindowTitle(f"Preview: {Path(file_path).name}")
                dialog.setModal(True)
                dialog.resize(600, 400)
                
                layout = QVBoxLayout(dialog)
                layout.addWidget(preview_widget)
                
                # Add close button
                close_btn = QPushButton("Close")
                close_btn.clicked.connect(dialog.accept)
                layout.addWidget(close_btn)
                
                dialog.exec_()
        else:
            # For other files, just open them
            self.open_file(file_path)
    
    def setup_context_menus(self):
        """Set up context menus for all views"""
        # Set up context menus for all views
        for view in [self.left_folder_view, self.left_file_view, 
                    self.right_folder_view, self.right_file_view]:
            view.setContextMenuPolicy(Qt.CustomContextMenu)
            view.customContextMenuRequested.connect(self.show_context_menu)
    
    def set_view_mode(self, pane_name, mode):
        """Set the view mode for a specific pane"""
        # Get the appropriate views and buttons
        if pane_name == "Left":
            folder_view = self.left_folder_view
            file_view = self.left_file_view
            buttons = self.left_view_buttons
        else:
            folder_view = self.right_folder_view
            file_view = self.right_file_view
            buttons = self.right_view_buttons
        # Uncheck all buttons
        for btn in buttons:
            btn.setChecked(False)
        # Check the selected button
        if mode == 'icon':
            buttons[0].setChecked(True)
        elif mode == 'column':
            buttons[1].setChecked(True)
        elif mode == 'thumbnail':
            buttons[2].setChecked(True)
        # Apply view mode to both views in the pane
        self.apply_view_mode_to_view(folder_view, mode)
        self.apply_view_mode_to_view(file_view, mode)
        # Store current view mode for this pane
        if pane_name == "Left":
            self.left_current_view_mode = mode
        else:
            self.right_current_view_mode = mode
    
    def set_icon_size(self, pane_name, size):
        """Set the icon size for a specific pane"""
        if pane_name == "Left":
            self.left_folder_view.setIconSize(QSize(size, size))
            self.left_file_view.setIconSize(QSize(size, size))
            # Adjust grid size based on icon size for consistent layout
            grid_size = size + 48  # Icon size + space for text
            self.left_folder_view.setGridSize(QSize(grid_size, grid_size))
            self.left_file_view.setGridSize(QSize(grid_size, grid_size))
        else:
            self.right_folder_view.setIconSize(QSize(size, size))
            self.right_file_view.setIconSize(QSize(size, size))
            # Adjust grid size based on icon size for consistent layout
            grid_size = size + 48  # Icon size + space for text
            self.right_folder_view.setGridSize(QSize(grid_size, grid_size))
            self.right_file_view.setGridSize(QSize(grid_size, grid_size))
    
    def apply_view_mode_to_view(self, view, mode):
        """Apply view mode to a specific view"""
        if mode == 'icon':
            self.restore_list_view(view)
            view.setViewMode(QListView.IconMode)
            view.setResizeMode(QListView.Adjust)
            icon_size = view.iconSize().width() if view.iconSize().width() > 0 else 32
            grid_size = icon_size + 48
            view.setGridSize(QSize(grid_size, grid_size))
            view.setSpacing(4)
            view.setWordWrap(True)
            view.setTextElideMode(Qt.ElideMiddle)
            view.setUniformItemSizes(False)
        elif mode == 'column':
            if isinstance(view, QListView):
                table_view = QTableView()
                if view == self.left_folder_view:
                    table_model = self.left_folder_table_model
                    pane_name = "Left"
                elif view == self.left_file_view:
                    table_model = self.left_file_table_model
                    pane_name = "Left"
                elif view == self.right_folder_view:
                    table_model = self.right_folder_table_model
                    pane_name = "Right"
                elif view == self.right_file_view:
                    table_model = self.right_file_table_model
                    pane_name = "Right"
                else:
                    table_model = self.left_folder_table_model
                    pane_name = "Left"
                table_view.setModel(table_model)
                table_view.setIconSize(QSize(16, 16))
                table_view.setAlternatingRowColors(True)
                table_view.setSortingEnabled(True)
                table_view.setSelectionBehavior(QTableView.SelectRows)
                table_view.setSelectionMode(QTableView.SingleSelection)
                header = table_view.horizontalHeader()
                header.setSectionsClickable(True)
                header.setStretchLastSection(True)
                header.setContextMenuPolicy(Qt.CustomContextMenu)
                header.customContextMenuRequested.connect(
                    lambda pos, tv=table_view, pn=pane_name: self.show_header_context_menu(pos, tv, pn)
                )
                header.setSectionResizeMode(0, QHeaderView.Interactive)
                header.setSectionResizeMode(1, QHeaderView.Interactive)
                header.setSectionResizeMode(2, QHeaderView.Interactive)
                header.setSectionResizeMode(3, QHeaderView.Interactive)
                table_view.setColumnWidth(0, 200)
                table_view.setColumnWidth(1, 80)
                table_view.setColumnWidth(2, 100)
                table_view.setColumnWidth(3, 150)
                table_view.resizeColumnsToContents()
                # Connect table view signals to appropriate handlers
                if view == self.left_folder_view:
                    table_view.clicked.connect(self.on_left_folder_clicked)
                    table_view.doubleClicked.connect(self.on_left_folder_clicked)
                elif view == self.left_file_view:
                    table_view.clicked.connect(self.on_left_file_clicked)
                    table_view.doubleClicked.connect(self.on_left_file_clicked)
                elif view == self.right_folder_view:
                    table_view.clicked.connect(self.on_right_folder_clicked)
                    table_view.doubleClicked.connect(self.on_right_folder_clicked)
                elif view == self.right_file_view:
                    table_view.clicked.connect(self.on_right_file_clicked)
                    table_view.doubleClicked.connect(self.on_right_file_clicked)
                if pane_name == "Left":
                    if view == self.left_folder_view:
                        self.left_folder_table_view = table_view
                    else:
                        self.left_file_table_view = table_view
                else:
                    if view == self.right_folder_view:
                        self.right_folder_table_view = table_view
                    else:
                        self.right_file_table_view = table_view
                self.replace_view_in_splitter(view, table_view)
        elif mode == 'thumbnail':
            self.restore_list_view(view)
            view.setViewMode(QListView.IconMode)
            view.setResizeMode(QListView.Adjust)
            view.setIconSize(QSize(128, 128))  # Larger icons for thumbnails
            grid_size = 160  # Larger grid for thumbnails
            view.setGridSize(QSize(grid_size, grid_size))
            view.setSpacing(8)
            view.setWordWrap(True)
            view.setTextElideMode(Qt.ElideMiddle)
            view.setUniformItemSizes(False)
            
            # Reload current directory to load thumbnails
            if view == self.left_folder_view or view == self.left_file_view:
                current_path = self.left_current_directory
                self.load_folders_to_model(self.left_folder_model, current_path)
                self.load_files_to_model(self.left_file_model, current_path)
            elif view == self.right_folder_view or view == self.right_file_view:
                current_path = self.right_current_directory
                self.load_folders_to_model(self.right_folder_model, current_path)
                self.load_files_to_model(self.right_file_model, current_path)
    
    def replace_view_in_splitter(self, old_view, new_view):
        """Replace a view in the splitter"""
        # Find the parent splitter and replace the view
        parent = old_view.parent()
        if parent:
            # Check if parent is a QSplitter
            if isinstance(parent, QSplitter):
                # Find the index of the old view in the splitter
                for i in range(parent.count()):
                    if parent.widget(i) == old_view:
                        parent.replaceWidget(i, new_view)
                        old_view.hide()
                        new_view.show()
                        break
            else:
                # Check if parent has a layout
                layout = parent.layout()
                if layout:
                    # Find the index of the old view
                    for i in range(layout.count()):
                        if layout.itemAt(i).widget() == old_view:
                            layout.removeWidget(old_view)
                            layout.insertWidget(i, new_view)
                            old_view.hide()
                            new_view.show()
                            break
    
    def go_back(self, pane_name):
        """Go back in history for a specific pane"""
        # This would implement back navigation
        logger.info(f"Go back in {pane_name} pane")
    
    def go_forward(self, pane_name):
        """Go forward in history for a specific pane"""
        # This would implement forward navigation
        logger.info(f"Go forward in {pane_name} pane")
    
    def go_up(self, pane_name):
        """Go up to parent directory for a specific pane"""
        if pane_name == "Left":
            current_path = self.left_current_directory
            parent_path = os.path.dirname(current_path)
            if parent_path != current_path:
                self.load_left_directory(parent_path)
        else:
            current_path = self.right_current_directory
            parent_path = os.path.dirname(current_path)
            if parent_path != current_path:
                self.load_right_directory(parent_path)
    
    def on_folder_selector_changed(self, pane_name, text):
        """Handle folder selector text change for a specific pane"""
        if os.path.isdir(text):
            if pane_name == "Left":
                self.load_left_directory(text)
            else:
                self.load_right_directory(text)
    
    def add_bookmark(self, pane_name):
        """Add current folder to bookmarks for a specific pane"""
        if pane_name == "Left":
            path = self.left_current_directory
        else:
            path = self.right_current_directory
        
        # This would add to bookmarks
        logger.info(f"Added bookmark for {pane_name} pane: {path}")
    
    def on_search_text_changed(self, pane_name, text):
        """Handle search text change for a specific pane"""
        self.apply_filters(pane_name)
    
    def on_sort_changed(self, pane_name, sort_type):
        """Handle sort type change for a specific pane"""
        if pane_name == "Left":
            folder_model = self.left_folder_model
            file_model = self.left_file_model
        else:
            folder_model = self.right_folder_model
            file_model = self.right_file_model
        
        if sort_type == 'Name':
            folder_model.sort(0, Qt.AscendingOrder)
            file_model.sort(0, Qt.AscendingOrder)
        elif sort_type == 'Size':
            folder_model.sort(0, Qt.AscendingOrder)
            file_model.sort(0, Qt.AscendingOrder)
        elif sort_type == 'Type':
            folder_model.sort(0, Qt.AscendingOrder)
            file_model.sort(0, Qt.AscendingOrder)
        elif sort_type == 'Date':
            folder_model.sort(0, Qt.AscendingOrder)
            file_model.sort(0, Qt.AscendingOrder)
    
    def apply_filters(self, pane_name):
        """Apply search filter to a specific pane"""
        if pane_name == "Left":
            search_box = self.left_search_box
            folder_model = self.left_folder_model
            file_model = self.left_file_model
        else:
            search_box = self.right_search_box
            folder_model = self.right_folder_model
            file_model = self.right_file_model
        
        search_text = search_box.text().lower()
        
        # Reload the current directory to reset filters
        if pane_name == "Left":
            current_path = self.left_current_directory
            self.load_folders_to_model(folder_model, current_path)
            self.load_files_to_model(file_model, current_path)
        else:
            current_path = self.right_current_directory
            self.load_folders_to_model(folder_model, current_path)
            self.load_files_to_model(file_model, current_path)
        
        # Apply search filter to folder model
        if search_text:
            for row in range(folder_model.rowCount() - 1, -1, -1):
                item = folder_model.item(row)
                if item and search_text not in item.text().lower():
                    folder_model.removeRow(row)
        
        # Apply search filter to file model
        if search_text:
            for row in range(file_model.rowCount() - 1, -1, -1):
                item = file_model.item(row)
                if item and search_text not in item.text().lower():
                    file_model.removeRow(row)
    
    def show_context_menu(self, position):
        """Show context menu for any view"""
        # This is a simplified context menu - you can expand it
        menu = QMenu()
        menu.addAction("Open")
        menu.addAction("Copy")
        menu.addAction("Delete")
        menu.exec_(self.sender().mapToGlobal(position))
    
    def show_header_context_menu(self, position, table_view, pane_name):
        """Show context menu for table header to add/remove columns"""
        menu = QMenu()
        
        # Get the table model
        model = table_view.model()
        if not isinstance(model, FileTableModel):
            return
        
        # Get all available columns and currently visible columns
        all_columns = model.getAllColumns()
        visible_columns = model.getVisibleColumns()
        
        # Add menu items for each column
        for i, column_name in enumerate(all_columns):
            action = menu.addAction(column_name)
            action.setCheckable(True)
            action.setChecked(i in visible_columns)
            action.triggered.connect(lambda checked, col_idx=i, tv=table_view: self.toggle_column(tv, col_idx, checked))
        
        menu.exec_(table_view.horizontalHeader().mapToGlobal(position))
    
    def toggle_column(self, table_view, column_index, show):
        """Toggle visibility of a column"""
        model = table_view.model()
        if not isinstance(model, FileTableModel):
            return
        
        visible_columns = model.getVisibleColumns()
        
        if show and column_index not in visible_columns:
            # Add column
            visible_columns.append(column_index)
            visible_columns.sort()  # Keep columns in order
        elif not show and column_index in visible_columns:
            # Remove column
            visible_columns.remove(column_index)
        
        model.setVisibleColumns(visible_columns)
    
    def restore_list_view(self, view):
        """Restore the original list view when switching from column view"""
        # Check if we have table views that need to be replaced
        if hasattr(self, 'left_folder_table_view') and view == self.left_folder_view:
            if self.left_folder_table_view and self.left_folder_table_view.parent():
                self.replace_view_in_splitter(self.left_folder_table_view, self.left_folder_view)
                self.left_folder_table_view = None
        elif hasattr(self, 'left_file_table_view') and view == self.left_file_view:
            if self.left_file_table_view and self.left_file_table_view.parent():
                self.replace_view_in_splitter(self.left_file_table_view, self.left_file_view)
                self.left_file_table_view = None
        elif hasattr(self, 'right_folder_table_view') and view == self.right_folder_view:
            if self.right_folder_table_view and self.right_folder_table_view.parent():
                self.replace_view_in_splitter(self.right_folder_table_view, self.right_folder_view)
                self.right_folder_table_view = None
        elif hasattr(self, 'right_file_table_view') and view == self.right_file_view:
            if self.right_file_table_view and self.right_file_table_view.parent():
                self.replace_view_in_splitter(self.right_file_table_view, self.right_file_view)
                self.right_file_table_view = None

def main():
    app = QApplication(sys.argv)
    win = FileManager()
    win.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main() 