import os
import requests
import random
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
import time
from datetime import datetime, timedelta
import re

class ImageCrawler:
    def __init__(self):
        self.base_url = "https://jandan.net/pic"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
            'Connection': 'keep-alive',
            'Referer': 'https://jandan.net/'
        }
        self.image_count = 0
        # 获取昨天的日期
        self.yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
        self.current_folder = self.yesterday
        
    def create_folder(self):
        """创建日期文件夹"""
        os.makedirs(self.current_folder, exist_ok=True)
        print(f"使用文件夹: {self.current_folder}")
        return self.current_folder
        
    def download_image(self, url):
        """下载并保存图片"""
        try:
            print(f"尝试下载图片: {url}")
            response = requests.head(url, headers=self.headers, timeout=10)
            
            # 检查文件类型
            content_type = response.headers.get('content-type', '').lower()
            if 'jpeg' not in content_type and 'jpg' not in content_type:
                print(f'跳过非jpg图片: {url} (类型: {content_type})')
                return False
                
            # 获取文件大小
            file_size = int(response.headers.get('content-length', 0))
            if file_size > 1024 * 1024:
                print(f'跳过大于1MB的图片: {url} ({file_size/1024/1024:.2f}MB)')
                return False
                
            # 下载图片
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                img = Image.open(BytesIO(response.content))
                
                # 生成文件名
                filename = f'{int(time.time())}_{self.image_count}.jpg'
                save_path = os.path.join(self.current_folder, filename)
                
                # 保存图片
                img.save(save_path, 'JPEG')
                self.image_count += 1
                print(f'成功下载: {save_path} ({file_size/1024:.1f}KB)')
                return True
                
        except Exception as e:
            print(f'下载失败 {url}: {str(e)}')
        return False
        
    def get_page_range(self):
        """获取指定日期的页面范围"""
        try:
            # 构造日期编码（例如：MjAyNTAyMjU-）
            date_code = f"MjAyNTAyMjU"  # 这里需要根据实际日期格式调整
            
            # 先访问主页面获取最新页码
            response = requests.get(self.base_url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找页面中的链接
            links = soup.find_all('a', href=re.compile(rf'/pic/{date_code}-\d+'))
            if not links:
                print("未找到页面链接")
                return None, None
            
            # 提取页码数字
            page_numbers = []
            for link in links:
                match = re.search(rf'{date_code}-(\d+)', link['href'])
                if match:
                    page_numbers.append(int(match.group(1)))
            
            if not page_numbers:
                print("未能解析页码")
                return None, None
            
            # 获取最大和最小页码
            start_page = max(page_numbers)
            end_page = min(page_numbers)
            
            print(f"获取到页面范围: {start_page} 到 {end_page}")
            return start_page, end_page
            
        except Exception as e:
            print(f"获取页面范围时出错: {e}")
            return None, None
        
    def crawl(self):
        """爬取图片"""
        try:
            # 创建日期文件夹
            self.create_folder()
            
            # 获取页面范围
            start_page, end_page = self.get_page_range()
            if start_page is None or end_page is None:
                print("无法获取页面范围，退出爬取")
                return
            
            # 遍历所有页面
            for page_num in range(start_page, end_page - 1, -1):
                # 构造页面URL
                page_url = f"{self.base_url}/MjAyNTAyMjUtMjE{page_num}"
                print(f"\n开始爬取页面: {page_url}")
                
                response = requests.get(page_url, headers=self.headers)
                if response.status_code != 200:
                    print(f"页面访问失败: {response.status_code}")
                    continue
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 找到所有图片链接
                image_links = []
                for link in soup.find_all('a', class_='view_img_link'):
                    href = link.get('href')
                    if href and href.lower().endswith(('.jpg', '.jpeg')):
                        image_links.append(href)
                
                print(f"在页面 {page_num} 中找到 {len(image_links)} 个图片链接")
                
                # 下载图片
                for img_url in image_links:
                    if not img_url.startswith('http'):
                        img_url = 'https:' + img_url if img_url.startswith('//') else 'https://' + img_url
                    
                    if self.download_image(img_url):
                        time.sleep(random.uniform(1, 2))  # 下载间隔
                
                time.sleep(random.uniform(2, 3))  # 页面间隔
                
        except Exception as e:
            print(f"爬取过程中出错: {e}")
        finally:
            print(f"\n爬取完成，共下载 {self.image_count} 张图片到文件夹 {self.current_folder}")

if __name__ == "__main__":
    crawler = ImageCrawler()
    crawler.crawl() 