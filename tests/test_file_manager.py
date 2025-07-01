import os
import sys
import tempfile
import shutil
import pytest

def test_package_import():
    """Test that the package can be imported"""
    try:
        import mac_file_manager_pro
        assert mac_file_manager_pro is not None
    except ImportError:
        # Fallback: add parent directory to path
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        import mac_file_manager_pro
        assert mac_file_manager_pro is not None

def test_file_manager_module_exists():
    """Test that the file_manager module exists"""
    try:
        import mac_file_manager_pro.file_manager
        assert mac_file_manager_pro.file_manager is not None
    except ImportError:
        # Fallback: add parent directory to path
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        import mac_file_manager_pro.file_manager
        assert mac_file_manager_pro.file_manager is not None

def test_file_operations(tmp_path):
    """Test basic file operations without GUI components"""
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