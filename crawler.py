import os
import requests
import random
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
import time
from datetime import datetime, timedelta
import re
from base64 import b64decode, b64encode
import logging
import pytz

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler('crawler.log'),
        logging.StreamHandler()
    ]
)

class ImageCrawler:
    def __init__(self):
        # 使用北京时间
        beijing_tz = pytz.timezone('Asia/Shanghai')
        now = datetime.now(beijing_tz)
        yesterday = now - timedelta(days=1)
        self.yesterday = yesterday.strftime('%Y%m%d')
        
        logging.info(f"当前工作目录: {os.getcwd()}")
        logging.info(f"目标日期: {self.yesterday}")
        
        self.base_url = "https://jandan.net/pic"
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
            'Connection': 'keep-alive',
            'Referer': 'https://jandan.net/',
            'DNT': '1',
            'Upgrade-Insecure-Requests': '1'
        }
        self.image_count = 0
        self.current_folder = os.path.join(os.getcwd(), self.yesterday)

    def create_folder(self):
        """创建日期文件夹"""
        try:
            os.makedirs(self.current_folder, exist_ok=True)
            logging.info(f"成功创建文件夹: {self.current_folder}")
            return self.current_folder
        except Exception as e:
            logging.error(f"创建文件夹失败: {e}")
            return None

    def download_image(self, url):
        """下载并保存图片"""
        try:
            logging.info(f"尝试下载图片: {url}")
            
            # 添加随机延迟
            time.sleep(random.uniform(1, 2))
            
            # 直接尝试下载图片
            response = self.session.get(url, headers=self.headers, timeout=10)
            if response.status_code != 200:
                logging.error(f"下载失败，状态码: {response.status_code}")
                return False
            
            # 检查文件大小
            content_length = len(response.content)
            if content_length > 1024 * 1024:  # 1MB
                logging.info(f'跳过大于1MB的图片: {url} ({content_length/1024/1024:.2f}MB)')
                return False
            
            try:
                # 尝试打开图片验证格式
                img = Image.open(BytesIO(response.content))
                if img.format.lower() not in ['jpeg', 'jpg']:
                    logging.info(f'跳过非JPG图片: {url} (格式: {img.format})')
                    return False
                
                # 生成文件名
                filename = f'{int(time.time())}_{self.image_count}.jpg'
                save_path = os.path.join(self.current_folder, filename)
                
                # 保存图片
                img.save(save_path, 'JPEG')
                self.image_count += 1
                logging.info(f'成功下载: {save_path} ({content_length/1024:.1f}KB)')
                return True
                
            except Exception as e:
                logging.error(f'图片处理失败: {str(e)}')
                return False
                
        except Exception as e:
            logging.error(f'下载失败 {url}: {str(e)}')
        return False

    def get_page_url(self, page_num):
        """生成页面URL"""
        try:
            # 构造页面ID：YYYYMMDD-XXX 格式
            date_str = self.yesterday
            page_str = f"{date_str}-{page_num}"
            # 转换为base64
            encoded = b64encode(page_str.encode()).decode().rstrip('=')
            return f"{self.base_url}/{encoded}"
        except Exception as e:
            logging.error(f"生成页面URL失败: {e}")
            return None

    def crawl(self):
        """爬取图片"""
        try:
            # 创建日期文件夹
            folder = self.create_folder()
            if not folder:
                logging.error("无法创建文件夹，退出爬取")
                return

            # 设置页码范围
            start_page = 219  # 起始页码
            end_page = 200    # 结束页码
            
            for page_num in range(start_page, end_page-1, -1):
                page_url = self.get_page_url(page_num)
                if not page_url:
                    continue
                    
                logging.info(f"正在检查页面: {page_url}")
                
                try:
                    # 添加随机延迟
                    time.sleep(random.uniform(2, 3))
                    
                    response = self.session.get(page_url, headers=self.headers)
                    if response.status_code != 200:
                        logging.error(f"页面访问失败: {response.status_code}")
                        continue

                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 查找所有图片链接
                    image_links = []
                    for link in soup.find_all('a', class_='view_img_link'):
                        if link.get('href'):
                            if link['href'].lower().endswith('.jpg'):
                                image_links.append(link['href'])
                    
                    logging.info(f"找到 {len(image_links)} 张jpg图片")
                    
                    # 下载图片
                    for img_url in image_links:
                        if not img_url.startswith('http'):
                            img_url = 'https:' + img_url if img_url.startswith('//') else 'https://' + img_url
                        
                        if self.download_image(img_url):
                            time.sleep(random.uniform(1, 2))

                except Exception as e:
                    logging.error(f"处理页面出错: {e}")
                    continue

            logging.info(f"爬取完成，共下载 {self.image_count} 张图片到文件夹 {self.current_folder}")

        except Exception as e:
            logging.error(f"爬取过程中出错: {e}")

if __name__ == "__main__":
    crawler = ImageCrawler()
    crawler.crawl() 