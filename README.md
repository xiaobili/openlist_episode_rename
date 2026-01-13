# OpenList 交互式剧集重命名工具

一个基于 Python 的交互式工具，用于连接 OpenList 服务并批量重命名剧集文件。该工具提供了直观的命令行界面，支持多种重命名模式，让剧集整理变得简单高效。

## 🚀 功能特性

### 核心功能
- **目录浏览** - 交互式导航 OpenList 文件系统
- **批量重命名** - 支持多种重命名模式的批量操作
- **剧集信息识别** - 自动从文件名中提取剧集信息
- **多模式重命名** - 智能识别、手动输入、统一样式等多种方式

### 重命名模式
- **智能重命名** - 自动识别文件名中的剧集信息并标准化
- **手动重命名** - 逐个为文件指定新名称
- **统一样式** - 为所有文件使用相同模式，自动递增集数
- **正则替换** - 使用正则表达式进行高级重命名

### 用户体验
- **Rich 界面** - 提供美观的终端界面（rich 版本）
- **进度指示** - 操作过程中的可视化进度条
- **确认机制** - 重命名前预览和确认
- **错误处理** - 完善的异常处理和错误提示

## 📋 系统要求

- Python 3.7+
- 网络连接到 OpenList 服务

## 🔧 依赖包

```bash
pip install requests rich
```


## 🛠️ 安装使用

### 1. 克隆或下载项目
```bash
# 下载项目文件
```


### 2. 安装依赖
```bash
pip install requests rich
```


### 3. 运行程序
```bash
# Rich 美化版（推荐）
python interactive_episode_renamer_with_rich.py

# 基础版本
python interactive_episode_renamer.py
```


## ⚙️ 配置参数

### 连接设置
- **服务地址**: OpenList 服务的 URL（如 `http://192.168.1.1:5244`）
- **用户名**: OpenList 账户用户名
- **密码**: OpenList 账户密码

### 支持的视频格式
`.mp4`, `.mkv`, `.avi`, `.mov`, `.wmv`, `.flv`, `.webm`, `.m4v`, `.mpg`, `.mpeg`, `.ts`, `.m2ts`, `.vob`, `.iso`

## 📖 使用指南

### 1. 登录验证
- 启动程序后输入 OpenList 服务地址
- 输入用户名和密码进行身份验证

### 2. 目录导航
- 选择数字进入子目录
- 0 键返回上级目录
- 查看当前目录的文件和子目录

### 3. 重命名操作
- 选择视频文件进行批量重命名
- 选择重命名模式：
  - **智能重命名**: 自动解析剧集信息
  - **手动重命名**: 逐一指定新名称
  - **统一样式**: 统一格式，递增集数

### 4. 命名模式示例
- `{title}.S{season}E{episode:02d}` → `权力的游戏.S01E01.mp4`
- `Season_{season}_Episode_{episode:02d}_{title}` → `Season_01_Episode_01_权力的游戏.mp4`

## 🔍 技术架构

### 主要组件
- **[InteractiveEpisodeRenamer](file:///Volumes/DATA/Code/Pycharm/Episode_Rename/interactive_episode_renamer_with_rich.py#L21-L587)** - 核心重命名类
- **API 集成** - 与 OpenList API 通信
- **文件系统操作** - 目录浏览和文件重命名

### API 接口
- `/api/auth/login` - 用户认证
- `/api/fs/list` - 获取目录内容
- `/api/fs/batch_rename` - 批量重命名

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request 来改进这个项目！

## 📄 许可证

遵循 MIT 许可证。详情请参阅 LICENSE 文件。

## 🆘 支持

如遇到问题，请检查：
1. OpenList 服务是否正常运行
2. 网络连接是否稳定
3. 用户名和密码是否正确
4. API 端点是否可用

---

*享受整洁有序的剧集收藏！*