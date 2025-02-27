import os
import requests
import random
from bs4 import BeautifulSoup
import time
from datetime import datetime, timedelta
import re
from base64 import b64decode, b64encode
import logging
import pytz
import base64
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

class ImageCrawler:
    def __init__(self):
        # 使用北京时间
        beijing_tz = pytz.timezone('Asia/Shanghai')
        now = datetime.now(beijing_tz)
        self.today = now.strftime('%Y%m%d')
        yesterday = now - timedelta(days=1)
        self.yesterday = yesterday.strftime('%Y%m%d')
        
        logging.info(f"目标日期: {self.yesterday}")
        
        self.base_url = "https://jandan.net/pic"
        self.session = requests.Session()
        
        # GitHub 配置
        self.github_token = os.environ.get('GITHUB_TOKEN')
        self.repo_owner = os.environ.get('GITHUB_REPOSITORY_OWNER')
        self.repo_name = os.environ.get('GITHUB_REPOSITORY').split('/')[-1]
        
        # 邮件配置
        self.smtp_server = "smtp.163.com"
        self.smtp_port = 465
        self.smtp_user = os.environ.get('SMTP_USER')  # 发件邮箱
        self.smtp_pass = os.environ.get('SMTP_PASS')  # 邮箱授权码
        self.notify_emails = ["psterman@163.com", "psterman@gmail.com", "2434775718@qq.com"]
        
        # 随机User-Agent列表
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15'
        ]
        
        self.image_count = 0

    def send_email_notification(self, repo_size_mb):
        """发送邮件通知"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_user
            msg['To'] = ', '.join(self.notify_emails)
            msg['Subject'] = f"仓库空间警告 - {self.repo_name}"
            
            body = f"""
            您的图片仓库 {self.repo_name} 已达到 {repo_size_mb:.2f}MB，
            即将超过 GitHub 仓库 1GB 的限制。
            请及时处理，以确保程序正常运行。
            
            当前时间：{datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # 连接SMTP服务器并发送邮件
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)
                
            logging.info("成功发送邮件通知")
            return True
            
        except Exception as e:
            logging.error(f"发送邮件失败: {str(e)}")
            return False

    def get_repo_size(self):
        """获取仓库大小（MB）"""
        try:
            headers = {
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            url = f'https://api.github.com/repos/{self.repo_owner}/{self.repo_name}'
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                repo_data = response.json()
                size_kb = repo_data.get('size', 0)  # GitHub API 返回的大小单位为KB
                size_mb = size_kb / 1024  # 转换为MB
                return size_mb
            else:
                logging.error(f"获取仓库大小失败: {response.status_code}")
                return None
                
        except Exception as e:
            logging.error(f"获取仓库大小出错: {str(e)}")
            return None

    def check_repo_size(self):
        """检查仓库大小并在需要时发送通知"""
        repo_size = self.get_repo_size()
        if repo_size is not None and repo_size > 900:  # 大于900MB时发送通知
            logging.warning(f"仓库大小已达到 {repo_size:.2f}MB，发送通知邮件")
            self.send_email_notification(repo_size)
            return True
        return False

    def get_random_headers(self):
        """获取随机User-Agent的请求头"""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
            'Connection': 'keep-alive',
            'Referer': 'https://jandan.net/'
        }

    def upload_to_github(self, file_content, file_path):
        """上传文件到GitHub"""
        try:
            # GitHub API endpoint
            url = f'https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/contents/{file_path}'
            
            headers = {
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            # 将文件内容转换为base64
            content = base64.b64encode(file_content).decode()
            
            # 准备请求数据
            data = {
                'message': f'Add image {file_path}',
                'content': content
            }
            
            # 检查文件是否已存在
            try:
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    # 文件已存在，获取其 SHA
                    data['sha'] = response.json()['sha']
            except:
                pass
            
            # 上传文件
            response = requests.put(url, headers=headers, data=json.dumps(data))
            
            if response.status_code in [201, 200]:
                return True
            else:
                logging.error(f"GitHub上传失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logging.error(f"GitHub上传出错: {str(e)}")
            return False

    def download_and_upload_image(self, url):
        """下载并上传图片到GitHub"""
        try:
            logging.info(f"处理图片: {url}")
            
            # 添加随机延迟
            time.sleep(random.uniform(0.5, 1))
            
            # 先获取文件头信息
            head_response = requests.head(url, headers=self.get_random_headers(), timeout=10)
            
            # 检查文件类型
            content_type = head_response.headers.get('content-type', '').lower()
            if 'jpeg' not in content_type and 'jpg' not in content_type:
                logging.info(f'跳过非jpg图片: {url}')
                return False
                
            # 获取文件大小（字节）
            file_size = int(head_response.headers.get('content-length', 0))
            
            # 检查文件大小是否小于1MB
            if file_size > 1024 * 1024:
                logging.info(f'跳过大于1MB的图片: {url} ({file_size/1024/1024:.2f}MB)')
                return False
            
            # 下载图片
            response = self.session.get(url, headers=self.get_random_headers(), timeout=10)
            if response.status_code != 200:
                logging.error(f"下载失败，状态码: {response.status_code}")
                return False
            
            try:
                # 生成文件名和路径
                filename = f'{int(time.time())}_{self.image_count}.jpg'
                file_path = f'{self.yesterday}/{filename}'
                
                # 上传到GitHub
                if self.upload_to_github(response.content, file_path):
                    self.image_count += 1
                    logging.info(f'成功上传: {file_path} ({file_size/1024:.1f}KB)')
                    return True
                    
            except Exception as e:
                logging.error(f'图片处理失败: {str(e)}')
                return False
                
        except Exception as e:
            logging.error(f'处理失败 {url}: {str(e)}')
        return False

    def get_page_url(self, page_num):
        """生成页面URL"""
        try:
            # 构造页面ID：YYYYMMDD-XXX 格式
            page_str = f"{self.yesterday}-{page_num}"
            # 转换为base64
            encoded = b64encode(page_str.encode()).decode().rstrip('=')
            return f"{self.base_url}/{encoded}"
        except Exception as e:
            logging.error(f"生成页面URL失败: {e}")
            return None

    def crawl(self):
        """爬取图片"""
        try:
            if not self.github_token:
                logging.error("未设置GITHUB_TOKEN环境变量")
                return
                
            if not self.smtp_user or not self.smtp_pass:
                logging.error("未设置邮箱配置环境变量")
                return
            
            # 检查仓库大小
            if self.check_repo_size():
                logging.warning("仓库接近大小限制，请及时处理")
                
            # 设置页码范围（从最新的页面开始）
            start_page = 219  # 起始页码
            end_page = 200    # 结束页码
            
            for page_num in range(start_page, end_page-1, -1):
                page_url = self.get_page_url(page_num)
                if not page_url:
                    continue
                    
                logging.info(f"正在检查页面: {page_url}")
                
                try:
                    # 添加随机延迟
                    time.sleep(random.uniform(1, 2))
                    
                    response = self.session.get(page_url, headers=self.get_random_headers())
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
                    
                    # 下载并上传图片
                    for img_url in image_links:
                        if not img_url.startswith('http'):
                            img_url = 'https:' + img_url if img_url.startswith('//') else 'https://' + img_url
                        
                        if self.download_and_upload_image(img_url):
                            time.sleep(random.uniform(0.5, 1))

                except Exception as e:
                    logging.error(f"处理页面出错: {e}")
                    time.sleep(random.uniform(3, 5))  # 出错后等待更长时间
                    continue

            logging.info(f"爬取完成，共上传 {self.image_count} 张图片")
            
            # 爬取完成后再次检查仓库大小
            self.check_repo_size()

        except Exception as e:
            logging.error(f"爬取过程中出错: {e}")

if __name__ == "__main__":
    crawler = ImageCrawler()
    crawler.crawl() 