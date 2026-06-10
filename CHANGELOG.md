# Changelog

本文记录 `office` 分支从 FishROS 安装器改造成办公软件安装器的主要提交和设计意图。

## Unreleased

### 修复搜狗输入法下载 403

- 搜狗输入法官方页面当前返回的 `ime-sec.gtimg.com` 安装包链接会出现 `403 Forbidden`。
- 安装器解析官方页面后会把同路径下载地址切换到可访问的 `ime.gtimg.com`。
- 内置备用地址同步改为 `ime.gtimg.com`，避免官方页面解析失败时继续命中 403 链接。

### 搜狗输入法安装器

- 新增菜单项 `[8]`：安装并配置搜狗输入法。
- 从搜狗输入法 Linux 官方页面解析当前架构对应的 `.deb` 下载地址。
- 支持 `amd64` 和 `arm64`。
- 安装 fcitx/Qt/im-config 相关依赖，并为当前用户写入 fcitx 输入法环境变量。
- 安装完成后提示注销并重新登录。

### 修复 frpc 解压函数缺失

- 补回 frpc 安装包的 `_safe_extract()` 安全解压函数。
- 修复下载成功后报 `Tool object has no attribute _safe_extract` 的问题。

### Python 下载代理兼容

- frpc 和 RustDesk 的 Python 流式下载显式支持 `http_proxy`、`https_proxy`、`all_proxy` 环境变量。
- 如果未设置代理但检测到 `127.0.0.1:7897` 可用，会自动使用该本地代理下载 GitHub release 资源。
- 放宽 release API 和安装包下载超时时间，避免 GitHub 直连或代理握手较慢时报错。

### 修复大文件下载卡住

- frpc 和 RustDesk 安装包下载改为 Python 原生流式下载。
- 避免 `CmdTask` 捕获 `wget` 进度输出时因 stdout/stderr 读取模型导致卡住。
- 仍然在终端显示下载地址、百分比、已下载大小和实时速度。

### 下载进度与网络可视化

- 入口脚本、运行时文件、翻译资源、工具脚本下载统一显示下载地址、进度条和下载速度。
- 当前菜单中的软件安装包下载也显示进度和速度，包括微信、QQ、VS Code、RustDesk 和 frpc。
- 便于异机测试时判断是下载源不可达、代理问题，还是 apt/systemd 阶段的问题。

### frpc SSH 内网穿透安装器

- 新增菜单项 `[7]`：安装并配置 frpc SSH 内网穿透。
- frpc 服务端配置参考本机配置：`frpc.jtcx.cn:7000`。
- 自动把本机 `127.0.0.1:22` 映射到远端 TCP 端口。
- 远端端口从 `2500` 开始探测，已占用则顺延递增，最大尝试到 `2599`。
- 安装 frpc 到 `/usr/local/bin/frpc`，配置写入 `/etc/frp/frpc.ini`。
- 创建 `/etc/systemd/system/frpc.service` 并启用开机自启。

### RustDesk 开机自启

- RustDesk 安装完成后尝试执行 `systemctl enable --now rustdesk`。
- 如果安装包未提供 `rustdesk.service`，会提示警告但不阻断服务器配置和固定密码设置。

### RustDesk 包选择优化

- RustDesk 安装工具优先选择 GitHub release 中当前架构对应的主线 `.deb` 包。
- 如果 release 中不存在非 `sciter` 的主线包，才回退使用 `sciter` 包。
- 这样可以避免在同时存在 Flutter 主线包和 Sciter 兼容包时，误装 `rustdesk-*-sciter.deb`。

## 97172fc - Set RustDesk permanent password

- RustDesk 安装完成后自动导入 ID/中继服务器配置。
- 自动设置固定密码，规则为：用户名首字母大写后拼接 `#2026`。
- 示例：`zzr` 对应密码 `Zzr#2026`。

## 1b685eb - Add RustDesk uninstall option

- 新增菜单项 `[6]`：卸载 RustDesk 并清理当前用户配置。
- 卸载流程包括 `apt remove`、`apt purge`、`apt autoremove` 和删除用户侧 RustDesk 配置目录。
- RustDesk 工具脚本通过菜单 `mode` 字段区分安装和卸载，避免复制两份脚本。

## bd2b0c9 - Add RustDesk installer

- 新增菜单项 `[5]`：安装并配置 RustDesk 远程控制。
- 自动识别 `amd64` / `arm64` 架构。
- 从 RustDesk GitHub 最新 release 查找对应 `.deb` 包并安装。
- 安装完成后导入预置 ID/中继服务器配置。

## 7b85775 - Document office installer testing and deployment

- README 增加异机测试说明。
- 补充局域网 HTTP、GitHub Raw、公网域名三种测试方式。
- 增加常见问题排查：默认域名、Raw 访问、局域网端口、sudo、apt 源等。

## 0e86b8f - Start office installer migration

- 将原 FishROS 安装器入口改造为办公软件安装器入口。
- 引入 `INSTALL_BASE_URL` 和 `/tmp/office_install`。
- 精简菜单，保留基础工具、微信、QQ、VS Code 等初始项。
- 新增基础工具包安装项，用于验证完整动态下载和工具执行链路。
