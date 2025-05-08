#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import shutil
import img2pdf
from PIL import Image
from tqdm import tqdm

def resource_path(relative_path):
    """获取资源的绝对路径，适配开发模式和打包模式"""
    try:
        base_path = sys._MEIPASS  # PyInstaller临时文件夹
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_user_choice():
    """用户交互：选择分辨率模式"""
    print("\n请选择分辨率处理方式：")
    print("1. 以第N张图片的分辨率为基准（默认第3张）")
    print("2. 自适应所有图片的最大分辨率")
    print("3. 自定义固定分辨率（如 800x600）")
    print("4. 统一横向分辨率，纵向不变（可能变形）")
    print("5. 统一纵向分辨率，横向不变（可能变形）")
    print("6. 不改变分辨率，直接输出（原图大小）")
    
    choice = input("请输入选项（1/2/3/4/5/6，默认1）：").strip() or "1"
    
    if choice == "1":
        n = input("请输入基准图片序号（如3，默认3）：").strip()
        return ("use_nth_image", int(n) if n.isdigit() else 3)
    elif choice == "2":
        return ("max_resolution", None)
    elif choice == "3":
        while True:
            size = input("请输入目标分辨率（格式：宽x高，如800x600）：").strip()
            if "x" in size.lower():
                try:
                    width, height = map(int, size.lower().split("x"))
                    return ("fixed_resolution", (width, height))
                except ValueError:
                    print("格式错误，请重新输入")
    elif choice == "4":
        width = input("请输入目标横向分辨率（如800）：").strip()
        return ("fixed_width", int(width) if width.isdigit() else 800)
    elif choice == "5":
        height = input("请输入目标纵向分辨率（如600）：").strip()
        return ("fixed_height", int(height) if height.isdigit() else 600)
    elif choice == "6":
        return ("original_size", None)
    else:
        return ("use_nth_image", 3)

def process_images():
    """主处理流程"""
    # 初始化路径（适配打包模式）
    base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.abspath(".")
    input_dir = os.path.join(base_dir, "input")
    output_dir = os.path.join(base_dir, "output")
    temp_dir = os.path.join(base_dir, "temp_pdf_images")
    
    # 创建必要目录
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(temp_dir, exist_ok=True)
    
    # 用户选择处理模式
    mode, param = get_user_choice()
    
    try:
        for folder_name in os.listdir(input_dir):
            folder_path = os.path.join(input_dir, folder_name)
            if not os.path.isdir(folder_path):
                continue
            
            # 获取图片文件并排序
            image_files = sorted([
                os.path.join(folder_path, f) 
                for f in os.listdir(folder_path) 
                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))
            ], key=lambda x: [int(c) if c.isdigit() else c for c in re.split('([0-9]+)', x)])
            
            if not image_files:
                print(f"跳过空文件夹: {folder_name}")
                continue
            
            # 计算目标分辨率
            if mode == "use_nth_image":
                n = min(param - 1, len(image_files) - 1)
                with Image.open(image_files[n]) as img:
                    target_size = img.size
            elif mode == "max_resolution":
                sizes = [Image.open(f).size for f in image_files]
                target_size = (max(w for w,_ in sizes), max(h for _,h in sizes))
            elif mode == "fixed_resolution":
                target_size = param
            else:
                target_size = None
            
            # 处理图片
            temp_images = []
            progress = tqdm(image_files, desc=f"处理 {folder_name}", unit="img")
            for img_path in progress:
                try:
                    if mode == "original_size":
                        # 原图模式：直接使用原图，只处理透明通道
                        img = Image.open(img_path)
                        if img.mode == 'RGBA':
                            img = img.convert('RGB')
                        temp_path = os.path.join(temp_dir, os.path.basename(img_path))
                        img.save(temp_path, quality=95)
                        temp_images.append(temp_path)
                    else:
                        # 其他模式：按原有逻辑处理
                        img = Image.open(img_path)
                        
                        # 调整尺寸
                        if mode == "fixed_width":
                            img = img.resize((param, img.size[1]), Image.LANCZOS)
                        elif mode == "fixed_height":
                            img = img.resize((img.size[0], param), Image.LANCZOS)
                        elif target_size and img.size != target_size:
                            img = img.resize(target_size, Image.LANCZOS)
                        
                        # 处理透明通道
                        if img.mode == 'RGBA':
                            img = img.convert('RGB')
                        
                        # 保存临时文件
                        temp_path = os.path.join(temp_dir, os.path.basename(img_path))
                        img.save(temp_path, quality=95)
                        temp_images.append(temp_path)
                except Exception as e:
                    print(f"\n处理失败: {img_path} - {str(e)}")
                    continue
            
            # 生成PDF
            if temp_images:
                pdf_path = os.path.join(output_dir, f"{folder_name}.pdf")
                with open(pdf_path, "wb") as f:
                    f.write(img2pdf.convert(temp_images))
                print(f"已生成: {pdf_path}")
    
    finally:
        # 清理临时文件
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

if __name__ == "__main__":
    import re  # 用于自然排序
    
    try:
        process_images()
    except Exception as e:
        print(f"\n程序出错: {str(e)}")
        if not getattr(sys, 'frozen', False):  # 开发模式下暂停
            input("按Enter退出...")
    finally:
        print("\n操作完成")
        if getattr(sys, 'frozen', False):  # 打包模式下保持窗口
            input("按Enter退出...")