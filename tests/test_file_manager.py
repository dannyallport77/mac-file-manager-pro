import os
import tempfile
import shutil
import pytest
from PyQt5.QtWidgets import QApplication
from file_manager import FilePanel

@pytest.fixture(scope="module")
def app():
    return QApplication([])

def test_filepanel_instantiation(app):
    panel = FilePanel()
    assert panel is not None

def test_set_folder(app):
    panel = FilePanel()
    temp_dir = tempfile.mkdtemp()
    try:
        panel.set_folder(temp_dir)
        assert panel.current_path == temp_dir
    finally:
        shutil.rmtree(temp_dir)

def test_file_operations(tmp_path):
    # Create a file
    file_path = tmp_path / "test.txt"
    file_path.write_text("hello")
    assert file_path.exists()
    # Copy file
    copy_path = tmp_path / "copy.txt"
    shutil.copy2(file_path, copy_path)
    assert copy_path.exists()
    # Move file
    move_path = tmp_path / "moved.txt"
    shutil.move(str(copy_path), move_path)
    assert move_path.exists()
    # Delete file
    move_path.unlink()
    assert not move_path.exists() 