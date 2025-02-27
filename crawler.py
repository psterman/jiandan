import os
import requests
import random
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
import time
from datetime import datetime, timedelta
import re
from base64 import b64decode
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
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Referer': 'https://jandan.net/',
            'Cookie': '_ga=GA1.1.123456789.1234567890'  # 添加一个通用的Cookie
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
            
            # 直接尝试下载图片，不进行 HEAD 请求
            response = requests.get(url, headers=self.headers, timeout=10)
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

    def is_yesterday_post(self, time_str):
        """判断是否是昨天的帖子"""
        try:
            beijing_tz = pytz.timezone('Asia/Shanghai')
            now = datetime.now(beijing_tz)
            yesterday = now - timedelta(days=1)
            yesterday_start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
            yesterday_end = yesterday_start + timedelta(days=1)

            logging.debug(f"检查时间字符串: {time_str}")
            
            # 处理时间格式
            if '@' in time_str:
                time_str = time_str.replace('@', '').strip()
            
            if '小时' in time_str:
                hours = int(re.search(r'(\d+)小时', time_str).group(1))
                post_time = now - timedelta(hours=hours)
                logging.debug(f"解析为{hours}小时前，发布时间: {post_time}")
            elif '分钟' in time_str:
                minutes = int(re.search(r'(\d+)分钟', time_str).group(1))
                post_time = now - timedelta(minutes=minutes)
                logging.debug(f"解析为{minutes}分钟前，发布时间: {post_time}")
            else:
                # 处理具体日期，如 "2024-02-26 10:30:00"
                try:
                    post_time = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    # 尝试其他可能的日期格式
                    try:
                        post_time = datetime.strptime(time_str, '%Y-%m-%d %H:%M')
                    except ValueError:
                        logging.error(f"无法解析时间格式: {time_str}")
                        return False
                post_time = beijing_tz.localize(post_time)
                logging.debug(f"解析为具体时间: {post_time}")

            is_yesterday = yesterday_start <= post_time < yesterday_end
            logging.debug(f"是否是昨天的帖子: {is_yesterday}")
            return is_yesterday
            
        except Exception as e:
            logging.error(f"解析时间失败: {time_str}, 错误: {e}")
            return False

    def crawl(self):
        """爬取图片"""
        try:
            # 创建日期文件夹
            folder = self.create_folder()
            if not folder:
                logging.error("无法创建文件夹，退出爬取")
                return

            # 获取主页
            logging.info("开始访问主页...")
            response = requests.get(self.base_url, headers=self.headers)
            if response.status_code != 200:
                logging.error(f"访问主页失败: {response.status_code}")
                return

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 获取最新页码
            latest_page = 1
            nav = soup.select('.cp-pagenavi a')
            for a in nav:
                href = a.get('href', '')
                if match := re.search(r'/pic/page-(\d+)|/pic/(\d+)', href):
                    page = int(match.group(1) or match.group(2))
                    latest_page = max(latest_page, page)

            logging.info(f"开始从第 {latest_page} 页查找昨天的图片")

            # 遍历页面查找昨天的图片
            found_yesterday = False
            for page in range(latest_page, 0, -1):
                page_url = f"{self.base_url}/page-{page}"
                logging.info(f"正在检查页面: {page_url}")

                try:
                    response = requests.get(page_url, headers=self.headers)
                    if response.status_code != 200:
                        logging.warning(f"页面访问失败: {response.status_code}")
                        continue

                    soup = BeautifulSoup(response.text, 'html.parser')
                    posts = soup.select('.commentlist li')
                    logging.info(f"在页面 {page} 找到 {len(posts)} 个帖子")

                    for post in posts:
                        # 获取发布时间
                        time_elem = post.select_one('.time')
                        if not time_elem:
                            continue
                        
                        post_time = time_elem.get_text().strip()
                        logging.info(f"检查帖子时间: {post_time}")
                        
                        if self.is_yesterday_post(post_time):
                            found_yesterday = True
                            logging.info("找到昨天的帖子")
                            
                            # 查找图片hash
                            img_hashes = post.select('.text .img-hash')
                            logging.info(f"找到 {len(img_hashes)} 个图片hash")
                            
                            for img_hash in img_hashes:
                                try:
                                    hash_text = img_hash.get_text().strip()
                                    img_url = b64decode(hash_text).decode()
                                    logging.info(f"解码图片URL: {img_url}")
                                    
                                    if not img_url.startswith('http'):
                                        img_url = 'https:' + img_url if img_url.startswith('//') else 'https://' + img_url
                                    
                                    if img_url.lower().endswith(('.jpg', '.jpeg')):
                                        self.download_image(img_url)
                                        time.sleep(random.uniform(1, 2))
                                except Exception as e:
                                    logging.error(f"处理图片链接失败: {e}")
                        elif found_yesterday and not self.is_yesterday_post(post_time):
                            # 如果已经找到昨天的帖子，且当前帖子不是昨天的，说明已经爬完了
                            logging.info("已完成昨天所有图片的爬取")
                            return

                    time.sleep(random.uniform(2, 3))

                except Exception as e:
                    logging.error(f"处理页面 {page} 时出错: {e}")

            logging.info(f"爬取完成，共下载 {self.image_count} 张图片到文件夹 {self.current_folder}")

        except Exception as e:
            logging.error(f"爬取过程中出错: {e}")

if __name__ == "__main__":
    crawler = ImageCrawler()
    crawler.crawl() 