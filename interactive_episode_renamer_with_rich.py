import requests
import json
import re
from typing import Dict, List, Optional
import os
import pickle
import configparser
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn
from rich import print as rprint
import getpass
import platform


class InteractiveEpisodeRenamer:
    def __init__(self, base_url: str, username: str, password: str):
        """
        交互式剧集重命名工具
        
        :param base_url: OpenList服务的基础URL
        :param username: 用户名
        :param password: 密码
        """
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.token = None
        self.current_path = "/"
        self.console = Console()
        if platform.system() == "Windows":
            self.token_file_path = os.path.join(os.environ.get("EPISODE_PATH", "USERPROFILE"), "token")
            self.config_file_path = os.path.join(os.environ.get("EPISODE_PATH", "USERPROFILE"), "episode_renamer.conf")
        elif platform.system() == "Linux":
            self.token_file_path = os.path.join(os.environ.get("EPISODE_PATH", "/tmp"), "token")
            self.config_file_path = os.path.join(os.environ.get("EPISODE_PATH", "/tmp"), "episode_renamer.conf")
        elif platform.system() == "Darwin":
            self.token_file_path = os.path.join(os.environ.get("EPISODE_PATH", "/tmp"), "token")
            self.config_file_path = os.path.join(os.environ.get("EPISODE_PATH", "/tmp"), "episode_renamer.conf")

    def save_config(self, base_url: str):
        """
        保存配置到本地文件
        """
        try:
            config = configparser.ConfigParser()
            
            # 确保配置目录存在
            config_dir = os.path.dirname(self.config_file_path)
            os.makedirs(config_dir, exist_ok=True)
            
            # 设置配置值
            config['DEFAULT'] = {
                'base_url': base_url,
            }
            
            with open(self.config_file_path, 'w', encoding='utf-8') as configfile:
                config.write(configfile)
            
            self.console.print(f"[green]✓[/green] 配置已保存到 {self.config_file_path}")
        except Exception as e:
            self.console.print(f"[red]✗[/red] 保存配置失败: {e}")

    def load_config(self) -> dict:
        """
        从本地文件加载配置
        """
        try:
            if os.path.exists(self.config_file_path):
                config = configparser.ConfigParser()
                config.read(self.config_file_path, encoding='utf-8')
                
                return {
                    'base_url': config.get('DEFAULT', 'base_url', fallback='http://192.168.1.1:5244')
                }
            else:
                return {
                    'base_url': 'http://192.168.1.1:5244'
                }
        except Exception as e:
            self.console.print(f"[red]✗[/red] 加载配置失败: {e}")
            return {
                'base_url': 'http://192.168.1.1:5244'
            }

    def validate_current_user(self) -> bool:
        """
        验证当前令牌是否属于当前用户
        """
        if not self.token:
            return False
            
        # 尝试获取用户信息来验证令牌的有效性
        try:
            headers = {
                "Authorization": self.token,
                "Content-Type": "application/json"
            }
            
            # 尝试获取用户信息
            user_info_url = f"{self.base_url}/api/me"
            response = requests.get(user_info_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            # 如果请求成功，则认为令牌有效
            if "code" in result and result["code"] == 200 and "data" in result:
                # 检查返回的用户名是否与当前输入的用户名一致
                if "username" in result["data"]:
                    returned_username = result["data"]["username"]
                    return returned_username == self.username
                # 如果返回的数据结构不同，可能包含用户ID或其他标识符
                elif "nick" in result["data"]:
                    returned_nick = result["data"]["nick"]
                    return returned_nick == self.username
                elif "name" in result["data"]:
                    returned_name = result["data"]["name"]
                    return returned_name == self.username
                # 如果没有用户名字段，至少验证令牌是有效的
                else:
                    return True
            return False
        except requests.exceptions.RequestException:
            # 如果 /api/me 不可用，尝试使用文件列表API作为备用验证方式
            try:
                headers = {
                    "Authorization": self.token,
                    "Content-Type": "application/json"
                }
                
                # 尝试访问根目录
                list_url = f"{self.base_url}/api/fs/list"
                payload = {"path": "/"}
                
                response = requests.post(list_url, json=payload, headers=headers, timeout=30)
                response.raise_for_status()
                
                result = response.json()
                # 如果请求成功(code为200)，则认为令牌有效
                # 但无法验证用户名，所以这里只验证令牌有效性
                return result.get("code") == 200
            except requests.exceptions.RequestException:
                return False

    def save_token(self):
        """
        将token保存到本地文件
        """
        try:
            # 确保目录存在
            token_dir = os.path.dirname(self.token_file_path)
            os.makedirs(token_dir, exist_ok=True)
            
            with open(self.token_file_path, 'wb') as f:
                pickle.dump(self.token, f)
            self.console.print(f"[green]✓[/green] 令牌已保存到 {self.token_file_path}")
        except Exception as e:
            self.console.print(f"[red]✗[/red] 保存令牌失败: {e}")

    def load_token(self) -> bool:
        """
        从本地文件加载token
        """
        try:
            if os.path.exists(self.token_file_path):
                with open(self.token_file_path, 'rb') as f:
                    self.token = pickle.load(f)
                self.console.print("[green]✓[/green] 从本地文件加载令牌成功")
                return True
            return False
        except Exception as e:
            self.console.print(f"[red]✗[/red] 加载令牌失败: {e}")
            return False

    def login(self) -> bool:
        """
        登录获取JWT令牌
        """
        login_url = f"{self.base_url}/api/auth/login"
        
        payload = {
            "username": self.username,
            "password": self.password
        }
        
        try:
            with Progress(
                SpinnerColumn(),
                *Progress.get_default_columns(),
                TimeElapsedColumn(),
                console=self.console
            ) as progress:
                task = progress.add_task("[cyan]正在登录...", total=None)
                
                response = requests.post(login_url, json=payload, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                progress.remove_task(task)
                
            if data.get("code") == 200:
                self.token = data["data"]["token"]
                self.console.print("[green]✓[/green] 登录成功，获取到JWT令牌")
                self.save_token()  # 登录成功后保存令牌
                return True
            else:
                self.console.print(f"[red]✗[/red] 登录失败: {data.get('message')}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.console.print(f"[red]✗[/red] 登录请求失败: {e}")
            return False

    def get_directory_contents(self, path: str = "/") -> Optional[List[Dict]]:
        """
        获取目录内容
        """
        if not self.token:
            self.console.print("[red]错误: 未登录，请先调用login方法[/red]")
            return None
            
        list_url = f"{self.base_url}/api/fs/list"
        
        payload = {
            "path": path
        }
        
        headers = {
            "Authorization": self.token,
            "Content-Type": "application/json"
        }
        
        try:
            with Progress(
                SpinnerColumn(),
                *Progress.get_default_columns(),
                TimeElapsedColumn(),
                console=self.console
            ) as progress:
                task = progress.add_task("[cyan]正在获取目录内容...", total=None)
                
                response = requests.post(list_url, json=payload, headers=headers, timeout=30)
                response.raise_for_status()
                
                result = response.json()
                progress.remove_task(task)
                
            if result.get("code") == 200:
                return result.get("data", {}).get("content", [])
            else:
                self.console.print(f"[red]✗[/red] 获取目录内容失败: {result.get('message')}")
                return None
                
        except requests.exceptions.RequestException as e:
            self.console.print(f"[red]✗[/red] 获取目录内容请求失败: {e}")
            return None

    def list_directories(self, path: str = "/") -> List[Dict]:
        """
        列出指定路径下的所有目录
        """
        contents = self.get_directory_contents(path)
        if not contents:
            return []
        
        directories = []
        for item in contents:
            if item.get('is_dir', False):
                directories.append(item)
        
        return directories

    def list_files(self, path: str = "/") -> List[Dict]:
        """
        列出指定路径下的所有文件
        """
        contents = self.get_directory_contents(path)
        if not contents:
            return []
        
        files = []
        for item in contents:
            if not item.get('is_dir', False):
                files.append(item)
        
        return files

    def batch_rename(self, src_dir: str, rename_mapping: Dict[str, str]) -> bool:
        """
        批量重命名文件
        
        :param src_dir: 源目录路径
        :param rename_mapping: 重命名映射字典，格式为 {原文件名: 新文件名}
        :return: 是否成功
        """
        if not self.token:
            self.console.print("[red]错误: 未登录，请先调用login方法[/red]")
            return False
            
        rename_url = f"{self.base_url}/api/fs/batch_rename"
        
        # 构建重命名对象列表
        rename_objects = []
        for src_name, new_name in rename_mapping.items():
            rename_objects.append({
                "src_name": src_name,
                "new_name": new_name
            })
        
        payload = {
            "src_dir": src_dir,
            "rename_objects": rename_objects
        }
        
        headers = {
            "Authorization": self.token,
            "Content-Type": "application/json"
        }
        
        try:
            with Progress(
                SpinnerColumn(),
                *Progress.get_default_columns(),
                TimeElapsedColumn(),
                console=self.console
            ) as progress:
                task = progress.add_task(f"[cyan]正在批量重命名 {len(rename_objects)} 个文件...", total=None)
                
                response = requests.post(rename_url, json=payload, headers=headers, timeout=60)
                response.raise_for_status()
                
                result = response.json()
                progress.remove_task(task)
                
            if result.get("code") == 200:
                self.console.print(f"[green]✓[/green] 批量重命名成功完成")
                self.console.print(f"[green]✓[/green] 处理了 {len(rename_objects)} 个文件")
                return True
            else:
                self.console.print(f"[red]✗[/red] 批量重命名失败: {result.get('message')}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.console.print(f"[red]✗[/red] 批量重命名请求失败: {e}")
            return False

    def rename_single_item(self, path: str, new_name: str) -> bool:
        """
        重命名单个文件或文件夹
        
        :param path: 文件或文件夹的完整路径
        :param new_name: 新名称
        :return: 是否成功
        """
        if not self.token:
            self.console.print("[red]错误: 未登录，请先调用login方法[/red]")
            return False
            
        rename_url = f"{self.base_url}/api/fs/rename"
        
        payload = {
            "path": path,
            "name": new_name
        }
        
        headers = {
            "Authorization": self.token,
            "Content-Type": "application/json"
        }
        
        try:
            with Progress(
                SpinnerColumn(),
                *Progress.get_default_columns(),
                TimeElapsedColumn(),
                console=self.console
            ) as progress:
                task = progress.add_task("[cyan]正在重命名单个项目...", total=None)
                
                response = requests.post(rename_url, json=payload, headers=headers, timeout=30)
                response.raise_for_status()
                
                result = response.json()
                progress.remove_task(task)
                
            if result.get("code") == 200:
                self.console.print(f"[green]✓[/green] 重命名成功: {os.path.basename(path)} -> {new_name}")
                return True
            else:
                self.console.print(f"[red]✗[/red] 重命名失败: {result.get('message')}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.console.print(f"[red]✗[/red] 重命名请求失败: {e}")
            return False

    def display_directories(self, path: str = "/"):
        """
        显示指定路径下的所有目录
        """
        directories = self.list_directories(path)
        
        if not directories:
            self.console.print("[yellow]该目录下没有子目录[/yellow]")
            return
        
        table = Table(title=f"路径 '{path}' 下的目录", expand=True)
        table.add_column("#", style="bold cyan", width=3)
        table.add_column("目录名称", style="magenta")
        
        for i, directory in enumerate(directories, 1):
            table.add_row(str(i), directory['name'])
        
        self.console.print(table)
        
        return directories

    def display_files(self, path: str = "/"):
        """
        显示指定路径下的所有文件
        """
        files = self.list_files(path)
        
        if not files:
            self.console.print("[yellow]该目录下没有文件[/yellow]")
            return
        
        table = Table(title=f"路径 '{path}' 下的文件", expand=True)
        table.add_column("#", style="bold cyan", width=3)
        table.add_column("文件名称", style="blue")
        table.add_column("大小", justify="right", style="green")
        
        for i, file in enumerate(files, 1):
            size = file.get('size', 0)
            size_str = self.human_readable_size(size)
            table.add_row(str(i), file['name'], size_str)
        
        self.console.print(table)
        
        return files

    def human_readable_size(self, size_bytes: int) -> str:
        """
        将字节大小转换为人类可读格式
        """
        if size_bytes == 0:
            return "0B"
        
        size_units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0
        size = float(size_bytes)
        
        while size >= 1024.0 and unit_index < len(size_units) - 1:
            size /= 1024.0
            unit_index += 1
        
        return f"{size:.1f}{size_units[unit_index]}"

    def navigate_to_directory(self, path: str = "/"):
        """
        导航到指定目录
        """
        self.current_path = path
        self.console.print(Panel(f"[bold blue]当前路径:[/bold blue] {self.current_path}", border_style="blue"))
        self.display_directories(path)
        self.display_files(path)

    def interactive_navigate(self):
        """
        交互式导航目录
        """
        while True:
            self.console.print(Panel(f"[bold blue]当前路径:[/bold blue] {self.current_path}", border_style="blue"))
            
            # 显示当前目录的子目录
            directories = self.list_directories(self.current_path)
            
            # 创建菜单选项
            menu_text = Text("请选择操作:", style="bold yellow")
            options_table = Table.grid(padding=(0, 2))
            options_table.add_column(style="bold cyan", width=4)
            options_table.add_column(style="white")
            
            options_table.add_row("0.", "返回上级目录")
            
            if directories:
                for i, directory in enumerate(directories, 1):
                    options_table.add_row(f"{i}.", f"进入目录: [magenta]{directory['name']}[/magenta]")
                
                options_table.add_row(f"{len(directories) + 1}.", "[green]查看当前目录文件[/green]")
                options_table.add_row(f"{len(directories) + 2}.", "[yellow]在当前目录进行批量重命名[/yellow]")
                options_table.add_row(f"{len(directories) + 3}.", "[blue]重命名单个文件或文件夹[/blue]")
                options_table.add_row(f"{len(directories) + 4}.", "[red]退出[/red]")
            else:
                # 即使没有子目录，也要显示文件查看和重命名选项
                options_table.add_row("1.", "[green]查看当前目录文件[/green]")
                options_table.add_row("2.", "[yellow]在当前目录进行批量重命名[/yellow]")
                options_table.add_row("3.", "[blue]重命名单个文件或文件夹[/blue]")
                options_table.add_row("4.", "[red]退出[/red]")
            
            self.console.print(menu_text)
            self.console.print(options_table)
            
            try:
                choice = Prompt.ask("\n请输入选项编号", default="0")
                choice_num = int(choice)
                
                if choice_num == 0:  # 返回上级目录
                    if self.current_path != "/":
                        parent_path = os.path.dirname(self.current_path)
                        if parent_path == "":
                            parent_path = "/"
                        self.navigate_to_directory(parent_path)
                
                elif directories and 1 <= choice_num <= len(directories):  # 进入选择的目录
                    selected_dir = directories[choice_num - 1]['name']
                    new_path = os.path.join(self.current_path, selected_dir)
                    # 处理根目录情况
                    if self.current_path == "/":
                        new_path = f"/{selected_dir}"
                    self.navigate_to_directory(new_path)
                
                elif directories:  # 有子目录的情况
                    if choice_num == len(directories) + 1:  # 查看当前目录文件
                        self.display_files(self.current_path)
                    elif choice_num == len(directories) + 2:  # 批量重命名
                        self.interactive_batch_rename()
                    elif choice_num == len(directories) + 3:  # 重命名单个项目
                        self.interactive_rename_single_item()
                    elif choice_num == len(directories) + 4:  # 退出
                        self.console.print("[green]退出程序[/green]")
                        break
                    else:
                        self.console.print("[red]无效的选择，请重新输入[/red]")
                
                else:  # 没有子目录的情况
                    if choice_num == 1:  # 查看当前目录文件
                        self.display_files(self.current_path)
                    elif choice_num == 2:  # 批量重命名
                        self.interactive_batch_rename()
                    elif choice_num == 3:  # 重命名单个项目
                        self.interactive_rename_single_item()
                    elif choice_num == 4:  # 退出
                        self.console.print("[green]退出程序[/green]")
                        break
                    else:
                        self.console.print("[red]无效的选择，请重新输入[/red]")
                    
            except ValueError:
                self.console.print("[red]请输入有效的数字[/red]")
            except KeyboardInterrupt:
                self.console.print("\n\n[red]程序被用户中断[/red]")
                break
            except Exception as e:
                self.console.print(f"[red]发生错误: {e}[/red]")

    def extract_episode_info(self, filename: str) -> Dict[str, str]:
        """
        从文件名中提取剧集信息
        
        :param filename: 原始文件名
        :return: 包含剧集信息的字典
        """
        # 常见的剧集文件名模式
        patterns = [
            r'(.+?)[\s._-]*S?(\d+)[\s._-]*E?(\d+)',  # S01E01 或 1x01 格式
            r'(.+?)[\s._-]*(\d+)[\s._-]*(\d{2})',    # 第1季第01集格式
            r'(.+?)[\s._-]*EP?[\s._-]*(\d+)',        # EP1 格式
            r'(.+?)[\s._-]*(\d+)[\s._-]*of[\s._-]*\d+',  # 1 of 10 格式
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) >= 2:
                    return {
                        'title': groups[0].strip(' ._-'),
                        'season': groups[1] if len(groups) > 1 else '1',
                        'episode': groups[2] if len(groups) > 2 else groups[1]
                    }
        
        # 如果没有匹配到模式，返回基本文件名信息
        name, ext = os.path.splitext(filename)
        return {
            'title': name,
            'season': '1',
            'episode': '1'
        }

    def generate_standard_name(self, episode_info: Dict[str, str], naming_pattern: str = "{title}.S{season}E{episode:02d}") -> str:
        """
        根据剧集信息和命名模式生成标准文件名
        
        :param episode_info: 剧集信息字典
        :param naming_pattern: 命名模式
        :return: 标准文件名
        """
        try:
            season = str(episode_info.get('season', '1')).zfill(2)
            episode = int(episode_info.get('episode', '1'))
            title = episode_info.get('title', 'Unknown').strip()
            
            # 清理标题中的特殊字符
            title = re.sub(r'[<>:"/\\|?*]', '_', title)
            
            return naming_pattern.format(season=season, episode=episode, title=title)
        except Exception as e:
            self.console.print(f"[red]生成标准名称时出错: {e}[/red]")
            return episode_info.get('title', 'Unknown')

    def interactive_batch_rename(self):
        """
        交互式批量重命名
        """
        self.console.print(Panel(f"[bold yellow]在路径 '{self.current_path}' 进行批量重命名[/bold yellow]", border_style="yellow"))
        
        # 获取当前目录的文件
        files = self.list_files(self.current_path)
        if not files:
            self.console.print("[yellow]当前目录没有文件[/yellow]")
            return
        
        # 过滤视频文件
        video_extensions = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg', '.ts', '.m2ts', '.vob', '.iso'}
        video_files = []
        
        for file in files:
            filename = file.get('name', '')
            ext = os.path.splitext(filename)[1].lower()
            if ext in video_extensions:
                video_files.append(file)
        
        if not video_files:
            self.console.print("[yellow]当前目录没有视频文件[/yellow]")
            return
        
        self.console.print(f"[cyan]找到 {len(video_files)} 个视频文件:[/cyan]")
        for i, file in enumerate(video_files, 1):
            self.console.print(f"  [bold]{i}.[/bold] {file['name']}")
        
        menu_text = Text("\n选择重命名方式:", style="bold yellow")
        options_table = Table.grid(padding=(0, 2))
        options_table.add_column(style="bold cyan", width=2)
        options_table.add_column(style="white")
        
        options_table.add_row("1.", "[blue]智能重命名（自动识别剧集信息）[/blue]")
        options_table.add_row("2.", "[blue]手动输入模式（为每个文件指定新名称）[/blue]")
        options_table.add_row("3.", "[blue]统一命名模式（为所有文件使用相同模式，递增集数）[/blue]")
        options_table.add_row("4.", "[blue]返回上级菜单[/blue]")
        
        self.console.print(menu_text)
        self.console.print(options_table)
        
        try:
            choice = Prompt.ask("\n请选择重命名方式", choices=["1", "2", "3", "4"], default="1")
            
            if choice == "1":
                self.smart_rename(video_files)
            elif choice == "2":
                self.manual_rename(video_files)
            elif choice == "3":
                self.unified_rename(video_files)
            elif choice == "4":
                return
            else:
                self.console.print("[red]无效的选择[/red]")
        
        except KeyboardInterrupt:
            self.console.print("\n\n[red]操作被用户中断[/red]")

    def smart_rename(self, video_files: List[Dict]):
        """
        智能重命名
        """
        self.console.print(Panel("[bold blue]智能重命名模式[/bold blue]", border_style="blue"))
        
        menu_text = Text("选择命名模式:", style="bold yellow")
        options_table = Table.grid(padding=(0, 2))
        options_table.add_column(style="bold cyan", width=2)
        options_table.add_column(style="white")
        
        options_table.add_row("1.", "[blue]标题.S01E01[/blue]")
        options_table.add_row("2.", "[blue]Season_01_Episode_01_标题[/blue]")
        options_table.add_row("3.", "[blue]自定义模式[/blue]")
        
        self.console.print(menu_text)
        self.console.print(options_table)
        
        try:
            choice = Prompt.ask("\n请选择命名模式", choices=["1", "2", "3"], default="1")
            
            if choice == "1":
                naming_pattern = "{title}.S{season}E{episode:02d}"
            elif choice == "2":
                naming_pattern = "Season_{season}_Episode_{episode:02d}_{title}"
            elif choice == "3":
                naming_pattern = Prompt.ask("请输入自定义命名模式 (例如: '{title}.S{season}E{episode:02d}')", 
                                           default="{title}.S{season}E{episode:02d}")
            else:
                self.console.print("[yellow]无效选择，使用默认模式[/yellow]")
                naming_pattern = "{title}.S{season}E{episode:02d}"
            
            # 创建重命名映射
            rename_mapping = {}
            for file in video_files:
                filename = file['name']
                ext = os.path.splitext(filename)[1]
                
                # 提取剧集信息
                episode_info = self.extract_episode_info(filename)
                episode_info['extension'] = ext
                
                # 生成新文件名
                new_name = self.generate_standard_name(episode_info, naming_pattern) + ext
                rename_mapping[filename] = new_name
            
            # 显示重命名计划
            self.console.print("\n[yellow]重命名计划:[/yellow]")
            plan_table = Table(expand=True)
            plan_table.add_column("原文件名", style="red", no_wrap=False)
            plan_table.add_column("→", style="bold white", justify="center")
            plan_table.add_column("新文件名", style="green", no_wrap=False)
            
            for old_name, new_name in rename_mapping.items():
                plan_table.add_row(old_name, "→", new_name)
            
            self.console.print(plan_table)
            
            confirm = Confirm.ask(f"\n确认执行重命名？这将重命名 {len(rename_mapping)} 个文件", default=False)
            if confirm:
                success = self.batch_rename(self.current_path, rename_mapping)
                if success:
                    self.console.print("[green]✓[/green] 批量重命名完成！")
                else:
                    self.console.print("[red]✗[/red] 批量重命名失败")
            else:
                self.console.print("[yellow]取消重命名[/yellow]")
        
        except KeyboardInterrupt:
            self.console.print("\n\n[red]操作被用户中断[/red]")

    def manual_rename(self, video_files: List[Dict]):
        """
        手动重命名
        """
        self.console.print(Panel("[bold blue]手动重命名模式[/bold blue]", border_style="blue"))
        self.console.print("[cyan]请为每个文件输入新名称:[/cyan]")
        
        rename_mapping = {}
        for file in video_files:
            old_name = file['name']
            new_name = Prompt.ask(f"\n'[blue]{old_name}[/blue]' 的新名称 (直接回车跳过)", default="")
            
            if new_name:
                rename_mapping[old_name] = new_name
            else:
                self.console.print("[yellow]跳过此文件[/yellow]")
        
        if rename_mapping:
            self.console.print("\n[yellow]重命名计划:[/yellow]")
            plan_table = Table(expand=True)
            plan_table.add_column("原文件名", style="red", no_wrap=False)
            plan_table.add_column("→", style="bold white", justify="center")
            plan_table.add_column("新文件名", style="green", no_wrap=False)
            
            for old_name, new_name in rename_mapping.items():
                plan_table.add_row(old_name, "→", new_name)
            
            self.console.print(plan_table)
            
            confirm = Confirm.ask(f"\n确认执行重命名？这将重命名 {len(rename_mapping)} 个文件", default=False)
            if confirm:
                success = self.batch_rename(self.current_path, rename_mapping)
                if success:
                    self.console.print("[green]✓[/green] 批量重命名完成！")
                else:
                    self.console.print("[red]✗[/red] 批量重命名失败")
            else:
                self.console.print("[yellow]取消重命名[/yellow]")
        else:
            self.console.print("[yellow]没有设置任何重命名[/yellow]")

    def unified_rename(self, video_files: List[Dict]):
        """
        统一命名模式 - 为所有文件使用相同模式，递增集数
        """
        self.console.print(Panel("[bold blue]统一命名模式[/bold blue]", border_style="blue"))
        self.console.print("[cyan]将为所有文件使用相同的命名模式，但集数会自动递增[/cyan]")
        
        # 获取用户输入
        show_name = Prompt.ask("请输入剧集名称")
        if not show_name:
            self.console.print("[red]剧集名称不能为空[/red]")
            return
            
        season = Prompt.ask("请输入季数", default="1")
        if not season or not season.isdigit():
            season = "1"
        else:
            season = str(int(season))
        
        start_episode = Prompt.ask("请输入起始集数", default="1")
        if not start_episode or not start_episode.isdigit():
            start_episode = "1"
        else:
            start_episode = str(int(start_episode))
        
        naming_pattern_input = Prompt.ask(
            "请选择命名模式:\n1. 剧名.S01E01\n2. Season_01_Episode_01_剧名\n3. 自定义模式\n请输入选择", 
            choices=["1", "2", "3"], 
            default="1"
        )
        
        if naming_pattern_input == "2":
            naming_pattern = "Season_{season}_Episode_{episode:02d}_{title}"
        elif naming_pattern_input == "3":
            naming_pattern = Prompt.ask(
                "请输入自定义命名模式 (例如: '{title}_S{season}E{episode:02d}')", 
                default="{title}.S{season}E{episode:02d}"
            )
        else:
            naming_pattern = "{title}.S{season}E{episode:02d}"
        
        # 创建重命名映射
        rename_mapping = {}
        current_episode = int(start_episode)
        
        for file in video_files:
            old_name = file['name']
            ext = os.path.splitext(old_name)[1]
            
            # 生成新文件名
            new_name = naming_pattern.format(
                season=season.zfill(2),
                episode=current_episode,
                title=show_name
            ) + ext
            
            rename_mapping[old_name] = new_name
            current_episode += 1  # 递增集数
        
        # 显示重命名计划
        self.console.print("\n[yellow]重命名计划:[/yellow]")
        plan_table = Table(expand=True)
        plan_table.add_column("原文件名", style="red", no_wrap=False)
        plan_table.add_column("→", style="bold white", justify="center")
        plan_table.add_column("新文件名", style="green", no_wrap=False)
        
        for old_name, new_name in rename_mapping.items():
            plan_table.add_row(old_name, "→", new_name)
        
        self.console.print(plan_table)
        
        confirm = Confirm.ask(f"\n确认执行重命名？这将重命名 {len(rename_mapping)} 个文件", default=False)
        if confirm:
            success = self.batch_rename(self.current_path, rename_mapping)
            if success:
                self.console.print("[green]✓[/green] 批量重命名完成！")
            else:
                self.console.print("[red]✗[/red] 批量重命名失败")
        else:
            self.console.print("[yellow]取消重命名[/yellow]")

    def regex_rename(self, video_files: List[Dict]):
        """
        正则替换重命名
        """
        self.console.print(Panel("[bold blue]正则替换模式[/bold blue]", border_style="blue"))
        
        try:
            pattern = Prompt.ask("请输入查找的正则表达式")
            if not pattern:
                self.console.print("[red]正则表达式不能为空[/red]")
                return
            
            replacement = Prompt.ask("请输入替换的内容 (可使用捕获组如 \\1, \\2)")
            
            rename_mapping = {}
            for file in video_files:
                old_name = file['name']
                new_name = re.sub(pattern, replacement, old_name)
                
                if new_name != old_name:
                    rename_mapping[old_name] = new_name
            
            if not rename_mapping:
                self.console.print("[yellow]没有匹配到任何文件[/yellow]")
                return
            
            self.console.print("\n[yellow]重命名计划:[/yellow]")
            plan_table = Table(expand=True)
            plan_table.add_column("原文件名", style="red", no_wrap=False)
            plan_table.add_column("→", style="bold white", justify="center")
            plan_table.add_column("新文件名", style="green", no_wrap=False)
            
            for old_name, new_name in rename_mapping.items():
                plan_table.add_row(old_name, "→", new_name)
            
            self.console.print(plan_table)
            
            confirm = Confirm.ask(f"\n确认执行重命名？这将重命名 {len(rename_mapping)} 个文件", default=False)
            if confirm:
                success = self.batch_rename(self.current_path, rename_mapping)
                if success:
                    self.console.print("[green]✓[/green] 批量重命名完成！")
                else:
                    self.console.print("[red]✗[/red] 批量重命名失败")
            else:
                self.console.print("[yellow]取消重命名[/yellow]")
        
        except re.error as e:
            self.console.print(f"[red]正则表达式错误: {e}[/red]")
        except KeyboardInterrupt:
            self.console.print("\n\n[red]操作被用户中断[/red]")

    def interactive_rename_single_item(self):
        """
        交互式重命名单个文件或文件夹
        """
        self.console.print(Panel(f"[bold blue]重命名单个文件或文件夹 - 当前路径: {self.current_path}[/bold blue]", border_style="blue"))
        
        # 获取当前目录的所有内容
        contents = self.get_directory_contents(self.current_path)
        if not contents:
            self.console.print("[yellow]当前目录为空或无法获取内容[/yellow]")
            return
        
        # 分别列出文件和目录
        files = [item for item in contents if not item.get('is_dir', False)]
        directories = [item for item in contents if item.get('is_dir', False)]
        
        self.console.print(f"\n[bold]当前路径 '{self.current_path}' 下的内容:[/bold]")
        
        # 创建表格显示内容
        content_table = Table(expand=True)
        content_table.add_column("序号", style="bold cyan", width=4)
        content_table.add_column("类型", style="bold yellow", width=6)
        content_table.add_column("名称", style="white")
        content_table.add_column("大小", style="green", justify="right")
        
        # 添加目录项
        for i, directory in enumerate(directories, 1):
            content_table.add_row(f"D{i}", "目录", directory['name'], "-")
        
        # 添加文件项
        for i, file in enumerate(files, len(directories) + 1):
            size = file.get('size', 0)
            size_str = self.human_readable_size(size)
            content_table.add_row(f"F{i}", "文件", file['name'], size_str)
        
        if contents:
            self.console.print(content_table)
        else:
            self.console.print("[yellow]当前目录下没有任何内容[/yellow]")
            return
        
        try:
            choice = Prompt.ask("\n请输入要重命名的项目编号 (例如 D1 或 F3，或直接输入名称)")
            
            selected_item = None
            selected_type = ""  # 'file' or 'dir'
            
            # 检查是否是通过编号选择
            if choice.lower().startswith('d') and choice[1:].isdigit():
                idx = int(choice[1:]) - 1
                if 0 <= idx < len(directories):
                    selected_item = directories[idx]
                    selected_type = "dir"
            elif choice.lower().startswith('f') and choice[1:].isdigit():
                idx = int(choice[1:]) - 1 - len(directories)
                if 0 <= idx < len(files):
                    selected_item = files[idx]
                    selected_type = "file"
            else:
                # 检查是否是直接输入名称
                for item in directories:
                    if item['name'] == choice:
                        selected_item = item
                        selected_type = "dir"
                        break
                if not selected_item:
                    for item in files:
                        if item['name'] == choice:
                            selected_item = item
                            selected_type = "file"
                            break
            
            if not selected_item:
                self.console.print("[red]未找到指定的项目[/red]")
                return
            
            old_name = selected_item['name']
            item_type = "目录" if selected_type == "dir" else "文件"
            self.console.print(f"[cyan]选择的项目: {old_name} (类型: {item_type})[/cyan]")
            
            new_name = Prompt.ask(f"\n请输入新的名称 (当前: {old_name})", default=old_name)
            
            if not new_name or new_name == old_name:
                if new_name == old_name:
                    self.console.print("[yellow]新名称与旧名称相同，无需重命名[/yellow]")
                else:
                    self.console.print("[red]新名称不能为空[/red]")
                return
            
            # 构建完整路径
            if self.current_path == "/":
                full_path = f"/{old_name}"
            else:
                full_path = f"{self.current_path}/{old_name}"
            
            confirm = Confirm.ask(f"\n确认将 '[blue]{old_name}[/blue]' 重命名为 '[green]{new_name}[/green]' ?", default=False)
            if confirm:
                success = self.rename_single_item(full_path, new_name)
                if success:
                    self.console.print("[green]✓[/green] 重命名成功完成！")
                else:
                    self.console.print("[red]✗[/red] 重命名失败")
            else:
                self.console.print("[yellow]取消重命名[/yellow]")
        
        except KeyboardInterrupt:
            self.console.print("\n\n[red]操作被用户中断[/red]")
        except Exception as e:
            self.console.print(f"[red]发生错误: {e}[/red]")


def main():
    """
    交互式主程序
    """
    console = Console()
    console.print(Panel("[bold blue]OpenList 交互式剧集重命名工具[/bold blue]", border_style="blue"))
    
    # 创建重命名实例
    renamer = InteractiveEpisodeRenamer("", "", "")
    
    # 从配置文件加载默认地址
    config = renamer.load_config()
    default_base_url = config['base_url']
    
    # 获取用户输入
    base_url = Prompt.ask("请输入OpenList服务地址", default=default_base_url)
    
    # 保存新的地址到配置文件
    renamer.save_config(base_url)
    
    username = Prompt.ask("请输入用户名")
    if not username:
        console.print("[red]用户名不能为空[/red]")
        return
    
    # 创建重命名实例
    renamer = InteractiveEpisodeRenamer(base_url, username, "")  # 初始时不需要密码
    
    # 尝试从本地文件加载令牌
    if renamer.load_token():
        # 验证令牌是否有效以及是否属于当前用户
        console.print("[cyan]正在验证本地令牌...[/cyan]")
        if renamer.validate_current_user():
            console.print("[green]✓[/green] 令牌验证成功，跳过登录步骤")
        else:
            console.print("[red]✗[/red] 令牌与当前用户不匹配或已过期，需要重新登录")
            password = getpass.getpass("请输入密码进行重新登录: ")
            renamer = InteractiveEpisodeRenamer(base_url, username, password)
            if not renamer.login():
                console.print("[red]无法登录到OpenList服务[/red]")
                return
    else:
        # 需要登录
        password = getpass.getpass("请输入密码: ")
        renamer = InteractiveEpisodeRenamer(base_url, username, password)
        if not renamer.login():
            console.print("[red]无法登录到OpenList服务[/red]")
            return
    
    # 开始交互式导航
    renamer.interactive_navigate()


if __name__ == "__main__":
    main()
