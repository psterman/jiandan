import requests
import os
import time
import random
from bs4 import BeautifulSoup
from datetime import datetime
import re
import json
import base64

# 创建保存目录和下载记录文件
if not os.path.exists('pic4'):
    os.makedirs('pic4')

# 随机User-Agent列表
user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15'
]

def get_random_headers():
    return {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
        'Connection': 'keep-alive',
        'Referer': 'https://jandan.net/'
    }

def download_image(url, filename):
    """下载图片，只下载小于1MB的jpg图片"""
    try:
        # 先获取文件头信息
        response = requests.head(url, headers=get_random_headers(), timeout=10)
        
        # 检查文件类型
        content_type = response.headers.get('content-type', '').lower()
        if 'jpeg' not in content_type and 'jpg' not in content_type:
            print(f'跳过非jpg图片: {filename}')
            return False
            
        # 获取文件大小（字节）
        file_size = int(response.headers.get('content-length', 0))
        
        # 检查文件大小是否小于1MB (1MB = 1024 * 1024 bytes)
        if file_size > 1024 * 1024:
            print(f'跳过大于1MB的图片: {filename} ({file_size/1024/1024:.2f}MB)')
            return False
            
        # 下载符合条件的图片
        response = requests.get(url, headers=get_random_headers(), timeout=10)
        if response.status_code == 200:
            with open(os.path.join('pic4', filename), 'wb') as f:
                f.write(response.content)
            print(f'成功下载: {filename} ({file_size/1024:.1f}KB)')
            return True
            
    except Exception as e:
        print(f'下载失败 {url}: {str(e)}')
    return False

def is_valid_date(post_time):
    start_date = datetime(2025, 2, 24, 0, 0)  # 开始时间：2月24日0点
    end_date = datetime(2025, 2, 25, 23, 59)  # 结束时间：2月25日23:59
    try:
        post_datetime = datetime.strptime(post_time, '%Y-%m-%d %H:%M:%S')
        return start_date <= post_datetime <= end_date  # 检查是否在范围内
    except:
        return False

def decode_image_url(encoded_string):
    """解码图片URL"""
    try:
        # 移除可能的 base64 前缀
        if ',' in encoded_string:
            encoded_string = encoded_string.split(',')[1]
        # 解码base64
        decoded = base64.b64decode(encoded_string).decode('utf-8')
        return decoded
    except:
        return None

def get_page_id(page_num):
    """生成页面ID"""
    # 格式：20250220-xxx，其中xxx是从219开始递减的页码
    start_page = 219  # 2月18日9点后的起始页
    current_page = start_page - (page_num - 1)
    date_str = "20250220"  # 固定日期
    page_str = f"{date_str}-{current_page}"
    # 转换为base64
    encoded = base64.b64encode(page_str.encode()).decode()
    return encoded

def get_post_time(soup):
    """获取页面中帖子的时间"""
    try:
        time_elements = soup.find_all('span', class_='time')
        if time_elements:
            for time_elem in time_elements:
                time_text = time_elem.text.strip()
                try:
                    post_time = datetime.strptime(time_text, '%Y-%m-%d %H:%M:%S')
                    return post_time
                except:
                    continue
    except Exception as e:
        print(f"获取时间出错: {e}")
    return None

def clean_duplicate_files():
    """清理所有pic文件夹中的重复文件，保留最新的文件"""
    try:
        # 获取所有pic开头的文件夹
        folders = [d for d in os.listdir('.') if d.startswith('pic') and os.path.isdir(d)]
        folder_files = {}
        for folder in folders:
            folder_files[folder] = set(os.listdir(folder))
        
        # 找出所有重复的文件名
        all_files = set()
        duplicate_files = set()
        for files in folder_files.values():
            for file in files:
                if file in all_files:
                    duplicate_files.add(file)
                all_files.add(file)
        
        if duplicate_files:
            print(f"\n发现{len(duplicate_files)}个重复文件，正在清理...")
            for filename in duplicate_files:
                # 找出所有包含该文件的文件夹
                containing_folders = []
                file_times = {}
                for folder in folder_files.keys():
                    if filename in folder_files[folder]:
                        file_path = os.path.join(folder, filename)
                        if os.path.exists(file_path):
                            containing_folders.append(folder)
                            file_times[folder] = os.path.getmtime(file_path)
                
                # 保留最新的文件
                if containing_folders:
                    newest_folder = max(containing_folders, key=lambda x: file_times[x])
                    for folder in containing_folders:
                        if folder != newest_folder:
                            file_path = os.path.join(folder, filename)
                            try:
                                os.remove(file_path)
                                print(f"删除旧文件: {file_path}")
                            except Exception as e:
                                print(f"删除文件失败 {file_path}: {e}")
                    
        print("文件清理完成")
        
        # 更新图片索引
        from generate_index import generate_image_index
        generate_image_index()
        
    except Exception as e:
        print(f"清理文件时出错: {e}")

def get_page_suffix(current_page):
    """获取页面后缀，使用base64编码"""
    # 构造页码字符串
    page_str = str(current_page)
    # 对页码进行base64编码
    encoded = base64.b64encode(page_str.encode()).decode()
    return encoded

def analyze_page_pattern(url):
    """分析页面导航，识别页码规律"""
    try:
        response = requests.get(url, headers=get_random_headers())
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 获取页面导航链接
        nav_links = []
        for link in soup.find_all('a', href=True):
            if '/pic/' in link['href']:
                nav_links.append(link['href'])
        
        # 提取页码和对应的URL尾数
        page_patterns = {}
        for link in nav_links:
            # 从URL中提取尾数
            match = re.search(r'MjAyNTAyMjctMjE([0-9a-z])#comments', link)
            if match:
                suffix = match.group(1)
                # 从链接文本中提取页码
                page_num = None
                link_text = link.get_text().strip()
                if link_text.isdigit():
                    page_num = int(link_text)
                    page_patterns[page_num] = suffix
        
        print("发现的页码规律：")
        for page, suffix in sorted(page_patterns.items(), reverse=True):
            print(f"页码 {page} -> 尾数 {suffix}")
            
        return page_patterns
    except Exception as e:
        print(f"分析页面规律时出错: {e}")
    return None

def main():
    # 先清理重复文件并更新index.html
    clean_duplicate_files()
    
    # 从200页开始，一直到180页
    current_page = 200  # 从200页开始
    end_page = 180  # 结束页码
    
    try:
        while current_page >= end_page:
            try:
                # 获取页面后缀
                page_suffix = get_page_suffix(current_page)
                # 修改URL格式以匹配实际页面
                url = f'https://jandan.net/pic/MjAyNTAyMjct{page_suffix}#comments'
                print(f"\n正在处理页面: {url}")
                print(f"当前页码: {current_page} (后缀: {page_suffix})")
                
                response = requests.get(url, headers=get_random_headers())
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 查找所有图片链接
                image_links = []
                for link in soup.find_all('a', class_='view_img_link'):
                    if link.get('href'):
                        # 只收集jpg链接
                        if link['href'].lower().endswith('.jpg'):
                            image_links.append(link['href'])
                
                if not image_links:
                    print(f"页面 {current_page} 没有找到jpg图片")
                    current_page -= 1
                    continue
                    
                print(f"找到 {len(image_links)} 张jpg图片")
                
                # 下载图片
                for img_url in image_links:
                    if not img_url.startswith('http'):
                        img_url = 'https:' + img_url if img_url.startswith('//') else 'https://' + img_url
                    
                    filename = img_url.split('/')[-1]
                    if download_image(img_url, filename):
                        time.sleep(random.uniform(0.5, 1))  # 下载间隔0.5-1秒
                
                print(f"完成页面 {current_page}")
                current_page -= 1  # 页码递减
                time.sleep(random.uniform(1, 2))  # 页面间隔1-2秒
                
            except Exception as e:
                print(f'处理页面 {current_page} 时出错: {str(e)}')
                print("等待3-5秒后继续...")
                time.sleep(random.uniform(3, 5))
                current_page -= 1
                continue
    finally:
        print("\n下载完成")

if __name__ == '__main__':
    main()