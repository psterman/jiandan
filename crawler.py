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
        
    def get_date_code(self):
        """获取日期编码"""
        yesterday = datetime.now() - timedelta(days=1)
        date_str = yesterday.strftime('%Y%m%d')
        # 将日期转换为Base64编码
        from base64 import b64encode
        date_code = b64encode(date_str.encode()).decode().rstrip('=')  # 移除末尾的=号
        return date_code
        
    def get_page_range(self):
        """获取指定日期的页面范围"""
        try:
            # 获取昨天的日期编码
            date_code = self.get_date_code()
            print(f"昨天的日期编码: {date_code}")
            
            # 先访问主页面
            response = requests.get(self.base_url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 找到页面导航链接
            nav_links = soup.select('.cp-pagenavi a')
            if not nav_links:
                print("未找到导航链接")
                return None, None
            
            # 提取所有页码
            page_numbers = []
            for link in nav_links:
                href = link.get('href', '')
                # 匹配形如 /pic/MjAyNTAyMjctMjE2 的链接
                match = re.search(rf'/pic/{date_code}-(\d+)', href)
                if match:
                    page_numbers.append(int(match.group(1)))
            
            if not page_numbers:
                print(f"未找到昨天({date_code})的页面")
                # 尝试访问第一页
                first_page_url = f"{self.base_url}/{date_code}-1"
                response = requests.get(first_page_url, headers=self.headers)
                if response.status_code == 200:
                    print("找到昨天第一页，从第一页开始爬取")
                    return 1, 1
                return None, None
            
            # 获取最大和最小页码
            start_page = max(page_numbers)
            # 往后多看5页，确保不遗漏
            end_page = max(1, start_page - 5)
            
            print(f"获取到昨天页面范围: {start_page} 到 {end_page}")
            return start_page, end_page
            
        except Exception as e:
            print(f"获取页面范围时出错: {e}")
            return None, None
        
    def get_yesterday_date_range(self):
        """获取昨天的日期范围"""
        yesterday = datetime.now() - timedelta(days=1)
        yesterday_start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_end = yesterday_start + timedelta(days=1)
        return yesterday_start, yesterday_end

    def is_yesterday_post(self, post_time_str):
        """判断帖子是否是昨天的帖子"""
        try:
            # 处理类似 "@1小时 ago" 或具体时间的情况
            if '小时' in post_time_str:
                hours_ago = int(post_time_str.split('小时')[0].replace('@', ''))
                post_time = datetime.now() - timedelta(hours=hours_ago)
            else:
                # 如果是具体日期，直接解析
                post_time = datetime.strptime(post_time_str, '%Y-%m-%d %H:%M')
            
            yesterday_start, yesterday_end = self.get_yesterday_date_range()
            return yesterday_start <= post_time < yesterday_end
        except Exception as e:
            print(f"解析时间失败: {post_time_str}, 错误: {e}")
            return False

    def find_first_page(self, start_page):
        """从第二页开始，倒推找到第一页"""
        try:
            date_code = self.get_date_code()
            
            # 从第二页开始
            current_page = start_page
            while current_page > 0:
                page_url = f"{self.base_url}/{date_code}-{current_page}"
                print(f"检查页面: {page_url}")
                
                response = requests.get(page_url, headers=self.headers)
                if response.status_code != 200:
                    print(f"页面访问失败: {response.status_code}")
                    break
                
                soup = BeautifulSoup(response.text, 'html.parser')
                posts = soup.select('.commentlist li')
                
                # 检查这一页是否全是昨天的内容
                all_yesterday_posts = all(
                    self.is_yesterday_post(post.select_one('.time').get_text().strip()) 
                    for post in posts if post.select_one('.time')
                )
                
                if all_yesterday_posts:
                    current_page -= 1
                else:
                    # 找到第一页
                    return current_page + 1
                
                time.sleep(random.uniform(1, 2))
            
            return current_page
        
        except Exception as e:
            print(f"查找第一页时出错: {e}")
            return None

    def crawl(self):
        """爬取图片"""
        try:
            # 创建日期文件夹
            self.create_folder()
            
            # 获取页面范围
            start_page, _ = self.get_page_range()
            if start_page is None:
                print("无法获取页面范围，退出爬取")
                return
            
            # 找到第一页
            first_page = self.find_first_page(start_page)
            if first_page is None:
                print("无法确定第一页，退出爬取")
                return
            
            # 遍历所有页面
            date_code = self.get_date_code()
            for page_num in range(start_page, first_page - 1, -1):
                page_url = f"{self.base_url}/{date_code}-{page_num}"
                print(f"\n开始爬取页面: {page_url}")
                
                response = requests.get(page_url, headers=self.headers)
                if response.status_code != 200:
                    print(f"页面访问失败: {response.status_code}")
                    continue
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 找到所有图片hash
                img_hashes = soup.select('.text .img-hash')
                print(f"在页面 {page_num} 中找到 {len(img_hashes)} 个图片链接")
                
                # 下载图片
                for img in img_hashes:
                    href = img.get_text().strip()
                    if href:
                        try:
                            img_url = b64decode(href.encode()).decode()
                            if img_url.lower().endswith(('.jpg', '.jpeg')):
                                if not img_url.startswith('http'):
                                    img_url = 'https:' + img_url if img_url.startswith('//') else 'https://' + img_url
                                
                                if self.download_image(img_url):
                                    time.sleep(random.uniform(1, 2))
                        except Exception as e:
                            print(f"解析图片链接失败: {e}")
                
                time.sleep(random.uniform(2, 3))  # 页面间隔
                
        except Exception as e:
            print(f"爬取过程中出错: {e}")
        finally:
            print(f"\n爬取完成，共下载 {self.image_count} 张图片到文件夹 {self.current_folder}")

if __name__ == "__main__":
    crawler = ImageCrawler()
    crawler.crawl() 