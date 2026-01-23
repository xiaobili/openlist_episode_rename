import requests
import json
import re
from typing import Dict, List, Optional
import os
import pickle
import configparser
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
            
            print(f"配置已保存到 {self.config_file_path}")
        except Exception as e:
            print(f"保存配置失败: {e}")

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
            print(f"加载配置失败: {e}")
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
            print(f"令牌已保存到 {self.token_file_path}")
        except Exception as e:
            print(f"保存令牌失败: {e}")

    def load_token(self) -> bool:
        """
        从本地文件加载token
        """
        try:
            if os.path.exists(self.token_file_path):
                with open(self.token_file_path, 'rb') as f:
                    self.token = pickle.load(f)
                print("从本地文件加载令牌成功")
                return True
            return False
        except Exception as e:
            print(f"加载令牌失败: {e}")
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
            response = requests.post(login_url, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if data.get("code") == 200:
                self.token = data["data"]["token"]
                print("登录成功，获取到JWT令牌")
                return True
            else:
                print(f"登录失败: {data.get('message')}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"登录请求失败: {e}")
            return False

    def get_directory_contents(self, path: str = "/") -> Optional[List[Dict]]:
        """
        获取目录内容
        """
        if not self.token:
            print("错误: 未登录，请先调用login方法")
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
            response = requests.post(list_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if result.get("code") == 200:
                return result.get("data", {}).get("content", [])
            else:
                print(f"获取目录内容失败: {result.get('message')}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"获取目录内容请求失败: {e}")
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
            print("错误: 未登录，请先调用login方法")
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
            response = requests.post(rename_url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            if result.get("code") == 200:
                print(f"批量重命名成功完成")
                print(f"处理了 {len(rename_objects)} 个文件")
                return True
            else:
                print(f"批量重命名失败: {result.get('message')}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"批量重命名请求失败: {e}")
            return False

    def rename_single_item(self, path: str, new_name: str) -> bool:
        """
        重命名单个文件或文件夹
        
        :param path: 文件或文件夹的完整路径
        :param new_name: 新名称
        :return: 是否成功
        """
        if not self.token:
            print("错误: 未登录，请先调用login方法")
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
            response = requests.post(rename_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if result.get("code") == 200:
                print(f"重命名成功: {os.path.basename(path)} -> {new_name}")
                return True
            else:
                print(f"重命名失败: {result.get('message')}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"重命名请求失败: {e}")
            return False

    def display_directories(self, path: str = "/"):
        """
        显示指定路径下的所有目录
        """
        directories = self.list_directories(path)
        
        if not directories:
            print("该目录下没有子目录")
            return
        
        print(f"\n路径 '{path}' 下的目录:")
        print("-" * 50)
        for i, directory in enumerate(directories, 1):
            print(f"{i}. {directory['name']}")
        print("-" * 50)
        
        return directories

    def display_files(self, path: str = "/"):
        """
        显示指定路径下的所有文件
        """
        files = self.list_files(path)
        
        if not files:
            print("该目录下没有文件")
            return
        
        print(f"\n路径 '{path}' 下的文件:")
        print("-" * 50)
        for i, file in enumerate(files, 1):
            size = file.get('size', 0)
            # 转换大小为人类可读格式
            size_str = self.human_readable_size(size)
            print(f"{i}. {file['name']} ({size_str})")
        print("-" * 50)
        
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
        print(f"\n当前路径: {self.current_path}")
        self.display_directories(path)
        self.display_files(path)

    def interactive_navigate(self):
        """
        交互式导航目录
        """
        while True:
            print(f"\n当前路径: {self.current_path}")
            
            # 显示当前目录的子目录
            directories = self.list_directories(self.current_path)
            
            print("请选择操作:")
            print("0. 返回上级目录")
            
            if directories:
                for i, directory in enumerate(directories, 1):
                    print(f"{i}. 进入目录: {directory['name']}")
                
                print(f"{len(directories) + 1}. 查看当前目录文件")
                print(f"{len(directories) + 2}. 在当前目录进行批量重命名")
                print(f"{len(directories) + 3}. 重命名单个文件或文件夹")
                print(f"{len(directories) + 4}. 退出")
            else:
                # 即使没有子目录，也要显示文件查看和重命名选项
                print("1. 查看当前目录文件")
                print("2. 在当前目录进行批量重命名")
                print("3. 重命名单个文件或文件夹")
                print("4. 退出")
            
            try:
                choice = input("\n请输入选项编号: ").strip()
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
                        print("退出程序")
                        break
                    else:
                        print("无效的选择，请重新输入")
                
                else:  # 没有子目录的情况
                    if choice_num == 1:  # 查看当前目录文件
                        self.display_files(self.current_path)
                    elif choice_num == 2:  # 批量重命名
                        self.interactive_batch_rename()
                    elif choice_num == 3:  # 重命名单个项目
                        self.interactive_rename_single_item()
                    elif choice_num == 4:  # 退出
                        print("退出程序")
                        break
                    else:
                        print("无效的选择，请重新输入")
                    
            except ValueError:
                print("请输入有效的数字")
            except KeyboardInterrupt:
                print("\n\n程序被用户中断")
                break
            except Exception as e:
                print(f"发生错误: {e}")

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
            print(f"生成标准名称时出错: {e}")
            return episode_info.get('title', 'Unknown')

    def interactive_batch_rename(self):
        """
        交互式批量重命名
        """
        print(f"\n在路径 '{self.current_path}' 进行批量重命名")
        
        # 获取当前目录的文件
        files = self.list_files(self.current_path)
        if not files:
            print("当前目录没有文件")
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
            print("当前目录没有视频文件")
            return
        
        print(f"\n找到 {len(video_files)} 个视频文件:")
        for i, file in enumerate(video_files, 1):
            print(f"{i}. {file['name']}")
        
        print("\n选择重命名方式:")
        print("1. 智能重命名（自动识别剧集信息）")
        print("2. 手动输入模式（为每个文件指定新名称）")
        print("3. 统一命名模式（为所有文件使用相同模式，递增集数）")
        print("4. 返回上级菜单")
        
        try:
            choice = input("\n请选择重命名方式 (1-4): ").strip()
            
            if choice == "1":
                self.smart_rename(video_files)
            elif choice == "2":
                self.manual_rename(video_files)
            elif choice == "3":
                self.unified_rename(video_files)
            elif choice == "4":
                return
            else:
                print("无效的选择")
        
        except KeyboardInterrupt:
            print("\n\n操作被用户中断")

    def smart_rename(self, video_files: List[Dict]):
        """
        智能重命名
        """
        print("\n智能重命名模式")
        print("选择命名模式:")
        print("1. 标题.S01E01")
        print("2. Season_01_Episode_01_标题")
        print("3. 自定义模式")
        
        try:
            choice = input("\n请选择命名模式 (1-3): ").strip()
            
            if choice == "1":
                naming_pattern = "{title}.S{season}E{episode:02d}"
            elif choice == "2":
                naming_pattern = "Season_{season}_Episode_{episode:02d}_{title}"
            elif choice == "3":
                naming_pattern = input("请输入自定义命名模式 (例如: '{title}.S{season}E{episode:02d}'): ").strip()
                if not naming_pattern:
                    naming_pattern = "{title}.S{season}E{episode:02d}"
            else:
                print("无效选择，使用默认模式")
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
            print("\n重命名计划:")
            for old_name, new_name in rename_mapping.items():
                print(f"  {old_name} -> {new_name}")
            
            confirm = input(f"\n确认执行重命名？这将重命名 {len(rename_mapping)} 个文件 (y/N): ").strip().lower()
            if confirm in ['y', 'yes']:
                success = self.batch_rename(self.current_path, rename_mapping)
                if success:
                    print("批量重命名完成！")
                else:
                    print("批量重命名失败")
            else:
                print("取消重命名")
        
        except KeyboardInterrupt:
            print("\n\n操作被用户中断")

    def manual_rename(self, video_files: List[Dict]):
        """
        手动重命名
        """
        print("\n手动重命名模式")
        print("请为每个文件输入新名称:")
        
        rename_mapping = {}
        for file in video_files:
            old_name = file['name']
            new_name = input(f"\n'{old_name}' 的新名称 (直接回车跳过): ").strip()
            
            if new_name:
                rename_mapping[old_name] = new_name
            else:
                print("跳过此文件")
        
        if rename_mapping:
            print("\n重命名计划:")
            for old_name, new_name in rename_mapping.items():
                print(f"  {old_name} -> {new_name}")
            
            confirm = input(f"\n确认执行重命名？这将重命名 {len(rename_mapping)} 个文件 (y/N): ").strip().lower()
            if confirm in ['y', 'yes']:
                success = self.batch_rename(self.current_path, rename_mapping)
                if success:
                    print("批量重命名完成！")
                else:
                    print("批量重命名失败")
            else:
                print("取消重命名")
        else:
            print("没有设置任何重命名")

    def unified_rename(self, video_files: List[Dict]):
        """
        统一命名模式 - 为所有文件使用相同模式，递增集数
        """
        print("\n统一命名模式")
        print("将为所有文件使用相同的命名模式，但集数会自动递增")
        
        # 获取用户输入
        show_name = input("请输入剧集名称: ").strip()
        if not show_name:
            print("剧集名称不能为空")
            return
            
        season = input("请输入季数 (默认为1): ").strip()
        if not season or not season.isdigit():
            season = "1"
        else:
            season = str(int(season))
        
        start_episode = input("请输入起始集数 (默认为1): ").strip()
        if not start_episode or not start_episode.isdigit():
            start_episode = "1"
        else:
            start_episode = str(int(start_episode))
        
        naming_pattern_input = input("请选择命名模式:\n1. 剧名.S01E01\n2. Season_01_Episode_01_剧名\n3. 自定义模式\n请输入选择 (1-3, 默认为1): ").strip()
        
        if naming_pattern_input == "2":
            naming_pattern = "Season_{season}_Episode_{episode:02d}_{title}"
        elif naming_pattern_input == "3":
            naming_pattern = input("请输入自定义命名模式 (例如: '{title}_S{season}E{episode:02d}'): ").strip()
            if not naming_pattern:
                naming_pattern = "{title}.S{season}E{episode:02d}"
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
        print("\n重命名计划:")
        for old_name, new_name in rename_mapping.items():
            print(f"  {old_name} -> {new_name}")
        
        confirm = input(f"\n确认执行重命名？这将重命名 {len(rename_mapping)} 个文件 (y/N): ").strip().lower()
        if confirm in ['y', 'yes']:
            success = self.batch_rename(self.current_path, rename_mapping)
            if success:
                print("批量重命名完成！")
            else:
                print("批量重命名失败")
        else:
            print("取消重命名")

    def regex_rename(self, video_files: List[Dict]):
        """
        正则替换重命名
        """
        print("\n正则替换模式")
        
        try:
            pattern = input("请输入查找的正则表达式: ").strip()
            if not pattern:
                print("正则表达式不能为空")
                return
            
            replacement = input("请输入替换的内容 (可使用捕获组如 \\1, \\2): ").strip()
            
            rename_mapping = {}
            for file in video_files:
                old_name = file['name']
                new_name = re.sub(pattern, replacement, old_name)
                
                if new_name != old_name:
                    rename_mapping[old_name] = new_name
            
            if not rename_mapping:
                print("没有匹配到任何文件")
                return
            
            print("\n重命名计划:")
            for old_name, new_name in rename_mapping.items():
                print(f"  {old_name} -> {new_name}")
            
            confirm = input(f"\n确认执行重命名？这将重命名 {len(rename_mapping)} 个文件 (y/N): ").strip().lower()
            if confirm in ['y', 'yes']:
                success = self.batch_rename(self.current_path, rename_mapping)
                if success:
                    print("批量重命名完成！")
                else:
                    print("批量重命名失败")
            else:
                print("取消重命名")
        
        except re.error as e:
            print(f"正则表达式错误: {e}")
        except KeyboardInterrupt:
            print("\n\n操作被用户中断")

    def interactive_rename_single_item(self):
        """
        交互式重命名单个文件或文件夹
        """
        print(f"\n重命名单个文件或文件夹 - 当前路径: {self.current_path}")
        
        # 获取当前目录的所有内容
        contents = self.get_directory_contents(self.current_path)
        if not contents:
            print("当前目录为空或无法获取内容")
            return
        
        # 分别列出文件和目录
        files = [item for item in contents if not item.get('is_dir', False)]
        directories = [item for item in contents if item.get('is_dir', False)]
        
        print(f"\n当前路径 '{self.current_path}' 下的内容:")
        print("-" * 50)
        
        # 显示目录
        if directories:
            print("目录:")
            for i, directory in enumerate(directories, 1):
                print(f"D{i}. {directory['name']}")
        
        # 显示文件
        if files:
            print("文件:")
            for i, file in enumerate(files, len(directories) + 1):
                size = file.get('size', 0)
                size_str = self.human_readable_size(size)
                print(f"F{i}. {file['name']} ({size_str})")
        
        print("-" * 50)
        
        if not contents:
            print("当前目录下没有任何内容")
            return
        
        try:
            choice = input("\n请输入要重命名的项目编号 (例如 D1 或 F3，或直接输入名称): ").strip()
            
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
                print("未找到指定的项目")
                return
            
            old_name = selected_item['name']
            print(f"\n选择的项目: {old_name} (类型: {'目录' if selected_type == 'dir' else '文件'})")
            
            new_name = input(f"请输入新的名称 (当前: {old_name}): ").strip()
            
            if not new_name:
                print("新名称不能为空")
                return
            
            if new_name == old_name:
                print("新名称与旧名称相同，无需重命名")
                return
            
            # 构建完整路径
            if self.current_path == "/":
                full_path = f"/{old_name}"
            else:
                full_path = f"{self.current_path}/{old_name}"
            
            confirm = input(f"\n确认将 '{old_name}' 重命名为 '{new_name}' ? (y/N): ").strip().lower()
            if confirm in ['y', 'yes']:
                success = self.rename_single_item(full_path, new_name)
                if success:
                    print("重命名成功完成！")
                else:
                    print("重命名失败")
            else:
                print("取消重命名")
        
        except KeyboardInterrupt:
            print("\n\n操作被用户中断")
        except Exception as e:
            print(f"发生错误: {e}")


def main():
    """
    交互式主程序
    """
    print("OpenList 交互式剧集重命名工具")
    print("=" * 40)
    
    # 创建重命名实例
    renamer = InteractiveEpisodeRenamer("", "", "")
    
    # 从配置文件加载默认地址
    config = renamer.load_config()
    default_base_url = config['base_url']
    
    # 获取用户输入
    base_url = input(f"请输入OpenList服务地址 (默认: {default_base_url}): ").strip()
    if not base_url:
        base_url = default_base_url
    
    # 保存新的地址到配置文件
    renamer.save_config(base_url)
    
    username = input("请输入用户名: ").strip()
    if not username:
        print("用户名不能为空")
        return
    
    import getpass
    # 创建重命名实例
    renamer = InteractiveEpisodeRenamer(base_url, username, "")
    
    # 尝试从本地文件加载令牌
    if renamer.load_token():
        # 验证令牌是否有效以及是否属于当前用户
        print("正在验证本地令牌...")
        # 尝试获取用户信息或验证令牌与用户名的匹配
        if renamer.validate_current_user():
            print("令牌验证成功，跳过登录步骤")
        else:
            print("令牌与当前用户不匹配或已过期，需要重新登录")
            password = getpass.getpass("请输入密码进行重新登录: ")
            renamer = InteractiveEpisodeRenamer(base_url, username, password)
            if not renamer.login():
                print("无法登录到OpenList服务")
                return
    else:
        # 登录
        password = getpass.getpass("请输入密码: ")
        renamer = InteractiveEpisodeRenamer(base_url, username, password)
        if not renamer.login():
            print("无法登录到OpenList服务")
            return
    
    # 开始交互式导航
    renamer.interactive_navigate()


if __name__ == "__main__":
    main()