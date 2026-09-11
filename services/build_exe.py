# build_exe.py - 用于打包为exe
import PyInstaller.__main__

PyInstaller.__main__.run([
    'main.py',
    '--onefile',
    '--console',
    '--name=tcp_data_server',
    '--hidden-import=flask',
    '--hidden-import=flask_cors',
    '--hidden-import=pymysql',
    '--add-data=config.py;.',
    '--add-data=api;api',
    '--add-data=database;database',
    '--add-data=tcp;tcp',
    '--add-data=utils;utils'
])