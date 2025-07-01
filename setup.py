from setuptools import setup, find_packages

setup(
    name='mac_file_manager_pro',
    version='1.2.3',
    packages=find_packages(),
    install_requires=[
        'PyQt5',
        'Pillow',
    ],
    entry_points={
        'gui_scripts': [
            'file-manager-pro = mac_file_manager_pro.file_manager:main',
        ],
    },
    include_package_data=True,
    author='Your Name',
    description='A dual-pane graphical file manager for macOS with advanced features.',
    license='MIT',
) 