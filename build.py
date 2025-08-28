import os
import sys
import PyInstaller.__main__
import shutil

# 清理之前的构建文件
if os.path.exists('build'):
    shutil.rmtree('build')
if os.path.exists('dist'):
    shutil.rmtree('dist')

# 确保资源文件存在
required_files = ['knock.mp3', 'mouse5.png', 'mouse10.png']
for file in required_files:
    if not os.path.exists(file):
        print(f"错误: 找不到必要的文件 {file}")
        sys.exit(1)

# 使用PyInstaller打包
PyInstaller.__main__.run([
    'main.py',  # 您的主脚本文件名
    '--onefile',
    '--windowed',  # 不显示控制台窗口
    '--add-data', 'knock.mp3:.',
    '--add-data', 'mouse5.png:.',
    '--add-data', 'mouse10.png:.',
    '--name', 'MouseTool',  # 可执行文件名称
    '--icon=icon.ico',  # 可选：添加图标
])