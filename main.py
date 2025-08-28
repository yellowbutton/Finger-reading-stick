import tkinter as tk
from PIL import Image, ImageTk
import threading
import time
import math
from pynput import keyboard
import pygame
import os
import sys
import tempfile
import atexit

# 判断是否在打包环境中运行
def resource_path(relative_path):
    """获取资源的绝对路径，支持开发环境和PyInstaller打包环境"""
    try:
        # PyInstaller创建的临时文件夹，存储资源文件
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

class ClickAnimationWindow:
    def __init__(self, parent):
        self.parent = parent
        self.window = tk.Toplevel(parent.root)
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.attributes("-transparentcolor", "white")
        self.window.geometry("200x200+0+0")  # 初始位置，稍后会移动
        
        self.canvas = tk.Canvas(self.window, width=200, height=200, bg='white', highlightthickness=0)
        self.canvas.pack()
        
        # 初始隐藏
        self.window.withdraw()
        
        # 动画参数
        self.radius = 10
        self.max_radius = 100
        self.is_animating = False
        
    def show_animation(self, x, y):
        if self.is_animating:
            return
            
        self.is_animating = True
        # 移动窗口到指定位置
        self.window.geometry(f"200x200+{x-100}+{y-100}")
        self.window.deiconify()
        
        self.start_time = time.time()
        self.animate()
    
    def animate(self):
        if not self.is_animating:
            return
            
        elapsed = time.time() - self.start_time
        progress = min(elapsed / 0.15, 1.0)
        
        # 计算当前半径（使用缓动函数使动画更平滑）
        t = progress
        current_radius = self.radius + (self.max_radius - self.radius) * (1 - (1 - t) * (1 - t))
        
        # 清除画布
        self.canvas.delete("all")
        
        # 绘制圆环
        self.canvas.create_oval(
            100 - current_radius, 100 - current_radius,
            100 + current_radius, 100 + current_radius,
            outline="#3498db", width=3
        )
        
        if progress < 1.0:
            self.window.after(10, self.animate)
        else:
            self.window.withdraw()
            self.is_animating = False

class MainApp:
    def __init__(self):
        # 初始化pygame音频
        try:
            pygame.mixer.init()
            print("Pygame mixer initialized successfully")
        except Exception as e:
            print(f"Error initializing pygame mixer: {e}")
        
        # 加载音频文件 - 使用resource_path函数
        self.knock_sound = None
        audio_path = resource_path("knock.mp3")
        if os.path.exists(audio_path):
            try:
                self.knock_sound = pygame.mixer.Sound(audio_path)
                print(f"Loaded audio file: {audio_path}")
            except Exception as e:
                print(f"Error loading audio file {audio_path}: {e}")
        else:
            print(f"Audio file not found: {audio_path}")
        
        self.root = tk.Tk()
        self.root.overrideredirect(True)  # 无边框
        self.root.attributes("-topmost", True)  # 始终置顶
        self.root.attributes("-transparentcolor", "#ffaec9")  # 设置透明色
        
        # 加载图像 - 使用resource_path函数
        try:
            mouse10_path = resource_path("mouse10.png")
            mouse5_path = resource_path("mouse5.png")
            
            self.original_image = Image.open(mouse10_path)
            self.small_image = Image.open(mouse5_path)  # 加载小图像
            
            self.photo = ImageTk.PhotoImage(self.original_image)
            self.small_photo = ImageTk.PhotoImage(self.small_image)
        except Exception as e:
            print(f"Error loading images: {e}")
            sys.exit(1)
        
        # 创建标签显示图像
        self.label = tk.Label(self.root, image=self.photo, bg="#ffaec9")
        self.label.pack()
        
        # 窗口初始位置和状态
        self.root.geometry("190x220+100+100")
        self.is_visible = False
        self.is_scaled = False
        self.original_width = 190
        self.original_height = 220
        
        # 创建动画窗口（预先创建，避免闪烁）
        self.animation_window = ClickAnimationWindow(self)
        
        # 设置键盘监听
        try:
            self.listener = keyboard.Listener(on_press=self.on_key_press, on_release=self.on_key_release)
            self.listener.start()
            print("Keyboard listener started")
        except Exception as e:
            print(f"Error starting keyboard listener: {e}")
            sys.exit(1)
        
        # 用于检测双击的变量
        self.last_ctrl_press_time = 0
        self.ctrl_press_count = 0
        self.ctrl_pressed = False  # 跟踪Ctrl键是否按下
        
        # 防止并发执行的锁
        self.animation_lock = threading.Lock()
        self.is_animating = False
        
        # 启动更新窗口位置的循环
        self.update_position()
        
        # 初始时隐藏窗口
        self.root.withdraw()
        
        print("Application started. Double press Ctrl to show/hide window.")
        
    def on_key_press(self, key):
        try:
            if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
                # 如果Ctrl键已经按下，忽略此次按下（防止长按）
                if self.ctrl_pressed:
                    print("Ctrl already pressed, ignoring")
                    return
                    
                self.ctrl_pressed = True
                current_time = time.time()
                
                # 检测双击（在0.1秒内按下两次Ctrl）
                if current_time - self.last_ctrl_press_time < 0.1:
                    self.ctrl_press_count += 1
                    print(f"Double press detected, count: {self.ctrl_press_count}")
                    if self.ctrl_press_count >= 2:
                        print("Toggling visibility")
                        self.toggle_visibility()
                        self.ctrl_press_count = 0
                        self.last_ctrl_press_time = 0  # 重置，避免连续多次触发
                else:
                    self.ctrl_press_count = 1
                    print("Single press detected")
                
                self.last_ctrl_press_time = current_time
                
                # 如果是单击且窗口可见，则触发缩放效果
                if self.is_visible and self.ctrl_press_count == 1:
                    print("Triggering click animation")
                    # 使用线程处理动画，避免阻塞主线程
                    threading.Thread(target=self.trigger_click_animation, daemon=True).start()
                    
        except Exception as e:
            print(f"Error in key press handler: {e}")
    
    def on_key_release(self, key):
        try:
            if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
                self.ctrl_pressed = False
                print("Ctrl released")
        except Exception as e:
            print(f"Error in key release handler: {e}")
    
    def toggle_visibility(self):
        self.is_visible = not self.is_visible
        if self.is_visible:
            self.root.deiconify()
            print("Window shown")
        else:
            self.root.withdraw()
            print("Window hidden")
    
    def update_position(self):
        if self.is_visible:
            # 获取鼠标位置
            x = self.root.winfo_pointerx() - 45
            y = self.root.winfo_pointery() - 5
            
            # 应用缩放偏移
            if self.is_scaled:
                x += 22  # 宽度缩小一半，偏移量减半
                y += 11  # 高度缩小一半，偏移量减半
            
            # 更新窗口位置
            self.root.geometry(f"+{x}+{y}")
        
        # 每10毫秒更新一次位置
        self.root.after(10, self.update_position)
    
    def trigger_click_animation(self):
        # 使用锁防止并发执行
        if not self.animation_lock.acquire(blocking=False):
            print("Animation already in progress, skipping")
            return  # 如果已经在执行动画，则跳过
            
        try:
            print("Starting animation")
            # 设置动画状态
            self.is_animating = True
            
            # 获取当前鼠标位置
            x = self.root.winfo_pointerx()
            y = self.root.winfo_pointery()
            
            # 缩放窗口
            self.scale_window()
            
            # 显示动画
            self.animation_window.show_animation(x, y)
            
            # 播放声音
            self.play_knock_sound()
            
            # 0.15秒后恢复窗口
            time.sleep(0.15)
            self.scale_window()
            
            print("Animation completed")
            
        except Exception as e:
            print(f"Error in animation: {e}")
        finally:
            # 释放锁并重置动画状态
            self.is_animating = False
            self.animation_lock.release()
    
    def play_knock_sound(self):
        if self.knock_sound:
            try:
                print("Playing sound")
                self.knock_sound.play()
            except Exception as e:
                print(f"Error playing sound: {e}")
        else:
            print("No sound to play")
    
    def scale_window(self):
        if not self.is_scaled:
            # 缩小窗口 - 使用预先准备好的小图像
            self.label.configure(image=self.small_photo)
            self.root.geometry("95x110")  # 缩小一半
            self.is_scaled = True
            print("Window scaled down")
        else:
            # 恢复窗口
            self.label.configure(image=self.photo)
            self.root.geometry("190x220")
            self.is_scaled = False
            print("Window restored to normal size")

if __name__ == "__main__":
    app = MainApp()
    app.root.mainloop()