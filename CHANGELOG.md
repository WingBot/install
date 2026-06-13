# Changelog

本文记录 `office` 分支从 FishROS 安装器改造成办公软件安装器的主要提交和设计意图。

## 2026-06-13 09:31:02 +0800 - Split public deployment into phases

- 将公网部署文档移动到项目根目录 `DEPLOY_PUBLIC_SERVER.md`。
- 部署方案改为两阶段：第一阶段只部署入口静态站点和域名，先安装 Clash/代理工具；第二阶段再配置 GitHub 反向代理和软件包缓存。
- README 中公网部署文档链接同步更新到根目录路径。

## 2026-06-13 09:14:41 +0800 - Add public server deployment guide

- 新增公网部署文档，说明如何用公网 IP 和域名部署安装器静态分发服务。
- 增加 Nginx、Certbot、DNS、项目同步、HTTPS 测试和客户端运行命令。
- 增加 GitHub Raw/Release 反向代理示例，支持白名单、公网 IP 校验、HEAD/GET 和大文件流式中转。
- 增加自托管软件包缓存站点方案，便于把常用 `.deb`、`.tar.gz` 放到自有域名下载。

## 2026-06-12 17:27:51 +0800 - Add Office font aliases

- 字体安装新增 Liberation、Carlito、Caladea 等可通过 apt 网络安装的 Office 替代字体。
- 写入 `/etc/fonts/conf.d/64-office-font-aliases.conf`，把 Microsoft YaHei、SimSun、DengXian、Calibri、Cambria 等常见 Windows/Office 字体名映射到 Linux 可用字体。
- 保留本机 Windows 字体导入作为精确字体方案；未挂载 Windows 字体目录时仍可使用网络安装的替代字体改善 WPS 展示。

## 2026-06-12 16:09:00 +0800 - Improve Windows font import

- Windows 字体导入不再只检查固定路径，新增 `/mnt/*/Windows/Fonts`、`/media/<user>/*/Windows/Fonts`、`/run/media/<user>/*/Windows/Fonts` 自动扫描。
- 支持通过 `WINDOWS_FONTS_DIR=/路径/Windows/Fonts` 手动指定字体来源目录。
- 未找到 Windows 字体目录时输出可操作提示，方便挂载 Windows 系统盘后重试。

## 2026-06-12 14:15:51 +0800 - Fix Zotero launcher icon

- Zotero 安装后不再手写指向 `chrome/icons/default/default256.png` 的图标路径。
- 安装器会优先把 Zotero 彩色图标安装到系统 hicolor 图标主题，并使用 `Icon=zotero` 写入桌面入口。
- Zotero 安装流程自动合并图标和桌面入口修复，不再单独暴露修复菜单项。

## 2026-06-12 14:06:54 +0800 - Fix Zotero and WPS downloads

- Zotero 安装包解压改为 `tarfile` 自动识别格式，兼容官方下载实际返回的 tar 包压缩格式，避免固定 `bz2` 导致 `not a bzip2 file`。
- WPS 下载按官网 `downLoad()` JavaScript 逻辑为 URL 追加 `t` 和 `k` 签名参数，修复裸 CDN 链接 `403 Forbidden`。
- WPS 下载增加浏览器 User-Agent、Referer，并保留代理失败后的直连重试。

## 2026-06-12 12:15:00 +0800 - Add office suite installers

- 新增菜单项 `[28]`：办公套件安装器，支持 Zotero、Obsidian、WPS Office、中文字体和 Windows 常用字体。
- Zotero 使用官方 Linux tarball 安装到 `/opt/zotero`，并写入命令和桌面入口。
- Obsidian 从 GitHub 最新 release 自动选择当前架构 deb；WPS 从 WPS Linux 官方页面解析 amd64 deb。
- 字体安装覆盖 Noto CJK、文泉驿、AR PL 中文字体、Microsoft core fonts，并尝试导入本机 Windows Fonts 目录。

## 2026-06-12 11:45:00 +0800 - Add AI coding assistant installers

- 新增菜单项 `[27]`：安装/卸载 AI 编程助手，支持 OpenAI Codex CLI、Claude Code 和 GitHub Copilot CLI。
- Codex 使用官方 npm 包 `@openai/codex`，Claude Code 使用 `@anthropic-ai/claude-code`，Copilot CLI 使用新的 `@github/copilot`。
- 安装器会检查 Node.js 版本，必要时自动调用 Node.js 安装器升级到当前最新 LTS；Copilot CLI 要求 Node.js 22+。
- README 增加账号登录和启动命令说明。

## 2026-06-12 11:23:38 +0800 - Avoid sudo when saving exit config

- 修复选择 `[0]` 退出安装器后，仍保存 `/tmp/office_install.yaml` 并可能触发 `sudo` 密码输入的问题。
- 退出安装器时不再生成配置记录；只有实际选择工具后才记录本次选择。
- 配置记录改为普通用户权限原子覆盖；无权限覆盖时只提示手动清理，不再主动调用 `sudo rm` 或 `sudo mv`。
- 生成记录路径支持通过 `OFFICE_INSTALL_RECORD_FILE` 覆盖，默认仍为 `/tmp/office_install.yaml`。

## 2026-06-12 11:12:09 +0800 - 调整常用软件为稳定最新版

- VS Code 改为使用 Microsoft stable 最新下载端点，不再固定 1.86.2 安装包。
- Node.js 默认版本改为动态检测当前最新 LTS 主版本，保留 22/20 作为兼容选项。
- 微信安装选项调整为默认推荐官方 Linux 最新版，Docker 版和旧桌面版作为备选。
- README 增加版本策略说明；Docker 已使用 Docker CE stable apt 仓库安装最新版，无需额外调整。

## 2026-06-12 11:02:47 +0800 - 新增 Google Chrome 安装器

- 新增菜单项 `[26]`：安装 Google Chrome 最新版。
- 从 Google 官方 Linux 直链下载 `google-chrome-stable_current_amd64.deb`，并通过 apt 安装。
- 安装器支持下载进度显示和本地代理检测；当前仅支持 `amd64` 架构。

## 2026-06-12 10:17:13 +0800 - 恢复 FishROS 原有工具菜单

- 恢复 office 迁移前 FishROS 原有 `[1]`-`[18]` 工具入口，包括 ROS、rosdep、ROS 环境、系统源、Docker、Cartographer、ROS Docker、NodeJs、OpenCode 等。
- 自有办公增强工具整体后移到 `[19]` 以后，避免破坏 FishROS 原工具之间的依赖编号。
- README 同步更新菜单编号，基础链路测试改为选择 `[19]` 基础工具包。
- 异机测试启动命令不变，仍通过 `wget` 下载入口脚本并设置 `INSTALL_BASE_URL` 运行；变化仅为菜单编号。

## 2026-06-12 10:06:22 +0800 - 补齐搜狗 logf 配置并简化 fcitx profile

- 搜狗输入法安装后自动补齐 `~/.config/sogoupinyin/logf.conf`，避免启动时反复提示 `parse logf.conf fail`。
- `EnabledIMList` 改为只保留 `sogoupinyin` 和 `fcitx-keyboard-us`，避免 fcitx profile 被写入大量键盘布局导致重复项和排查困难。

## 2026-06-12 10:06:22 +0800 - 修复搜狗输入法缺少 libgsettings-qt

- 搜狗输入法依赖增加 `libgsettings-qt1`，修复 `/opt/sogoupinyin/files/bin/sogoupinyin-service` 启动时报 `libgsettings-qt.so.1` 缺失。
- 同步增加 `qml-module-gsettings1.0`，补齐 GSettings 的 Qt/QML 运行依赖。

## 2026-06-12 10:00:51 +0800 - 自动切换搜狗为当前 fcitx 输入法

- 搜狗输入法安装后自动把 `~/.config/fcitx/profile` 中的 `IMName` 设置为 `sogoupinyin`。
- 自动确保 `EnabledIMList` 中 `sogoupinyin` 启用，减少只停留在 `fcitx-keyboard-us` 导致无法输入中文的问题。
- 自动把 fcitx 默认输入法状态设置为 `Active`。

## 2026-06-12 09:30:09 +0800 - 修复搜狗输入法 fcitx 启动崩溃

- 不再通过 `CmdTask` 直接运行 `fcitx -r -d`，避免 fcitx daemon 持有输出管道导致安装器 `ret_code` 缺失崩溃。
- 改为使用非阻塞后台进程尝试重启 fcitx，失败时只提示警告，不阻断安装流程。
- 启动前确保 `~/.config/sogoupinyin` 存在并归属目标用户，减少 `logf.conf fail` 这类配置目录问题。

## 2026-06-11 10:50:36 +0800 - 补强搜狗输入法 fcitx 会话配置

- 搜狗输入法安装器增加 `fcitx-tools`、`fcitx-ui-classic`、`fcitx-module-dbus`、`fcitx-module-kimpanel` 依赖。
- 安装后显式写入 `~/.xinputrc` 为 `run_im fcitx`，减少 `im-config` 与 `ibus` 残留配置冲突。
- 安装后写入 `~/.config/autostart/fcitx.desktop`，确保图形登录后启动 `fcitx -r -d`。
- README 根据实际 X11/fcitx 环境输出，补充搜狗 addon、当前输入法和 ibus 竞争排查命令。

## 2026-06-11 10:30:31 +0800 - 修复 Zellij Tab 乱码与补充测试说明

- Zellij 默认配置改为 `simplified_ui true` 并关闭 `pane_frames`，避免缺少 Nerd Font/Powerline 字体时 Tab 标签前后出现乱码。
- README 增加 Zellij 已安装机器的 Tab 乱码手动修复方式。
- README 增加开启 Clash/系统代理/TUN 时的局域网安装器绕过代理命令。
- README 增加搜狗输入法安装后无法输入中文的常见原因和排查命令。

## 2026-06-11 09:18:54 +0800 - Zellij 与 Oh My Zsh 安装器

- 新增菜单项 `[9]`：安装并配置 Zellij 终端复用器。
- Zellij 从 GitHub 最新 release 自动选择当前架构安装包，安装到 `/usr/local/bin/zellij`。
- 写入默认 `~/.config/zellij/config.kdl`，启用鼠标滚轮查看历史输出、选择文本自动复制到系统剪贴板。
- 新增 `/usr/local/bin/office-zellij-copy`，Wayland 使用 `wl-copy`，X11 使用 `xclip`。
- 新增菜单项 `[10]`：安装并配置 Oh My Zsh。
- Oh My Zsh 会安装 zsh、git、Powerline 字体，克隆官方框架和 `zsh-autosuggestions`、`zsh-syntax-highlighting` 插件。
- 写入默认 `.zshrc`，并尝试把当前用户默认 shell 切换为 zsh。

## 2026-06-10 23:24:54 +0800 - 修复搜狗输入法下载 403

- 搜狗输入法官方页面当前返回的 `ime-sec.gtimg.com` 安装包链接会出现 `403 Forbidden`。
- 安装器解析官方页面后会把同路径下载地址切换到可访问的 `ime.gtimg.com`。
- 内置备用地址同步改为 `ime.gtimg.com`，避免官方页面解析失败时继续命中 403 链接。

## 2026-06-10 23:13:04 +0800 - 搜狗输入法安装器

- 新增菜单项 `[8]`：安装并配置搜狗输入法。
- 从搜狗输入法 Linux 官方页面解析当前架构对应的 `.deb` 下载地址。
- 支持 `amd64` 和 `arm64`。
- 安装 fcitx/Qt/im-config 相关依赖，并为当前用户写入 fcitx 输入法环境变量。
- 安装完成后提示注销并重新登录。

## 2026-06-10 22:07:13 +0800 - 修复 frpc 解压函数缺失

- 补回 frpc 安装包的 `_safe_extract()` 安全解压函数。
- 修复下载成功后报 `Tool object has no attribute _safe_extract` 的问题。

## 2026-06-10 16:26:32 +0800 - Python 下载代理兼容

- frpc 和 RustDesk 的 Python 流式下载显式支持 `http_proxy`、`https_proxy`、`all_proxy` 环境变量。
- 如果未设置代理但检测到 `127.0.0.1:7897` 可用，会自动使用该本地代理下载 GitHub release 资源。
- 放宽 release API 和安装包下载超时时间，避免 GitHub 直连或代理握手较慢时报错。

## 2026-06-10 16:17:14 +0800 - 修复大文件下载卡住

- frpc 和 RustDesk 安装包下载改为 Python 原生流式下载。
- 避免 `CmdTask` 捕获 `wget` 进度输出时因 stdout/stderr 读取模型导致卡住。
- 仍然在终端显示下载地址、百分比、已下载大小和实时速度。

## 2026-06-10 16:11:02 +0800 - 下载进度与网络可视化

- 入口脚本、运行时文件、翻译资源、工具脚本下载统一显示下载地址、进度条和下载速度。
- 当前菜单中的软件安装包下载也显示进度和速度，包括微信、QQ、VS Code、RustDesk 和 frpc。
- 便于异机测试时判断是下载源不可达、代理问题，还是 apt/systemd 阶段的问题。

## 2026-06-10 16:01:10 +0800 - frpc SSH 内网穿透安装器

- 新增菜单项 `[7]`：安装并配置 frpc SSH 内网穿透。
- frpc 服务端配置参考本机配置：`frpc.jtcx.cn:7000`。
- 自动把本机 `127.0.0.1:22` 映射到远端 TCP 端口。
- 远端端口从 `2500` 开始探测，已占用则顺延递增，最大尝试到 `2599`。
- 安装 frpc 到 `/usr/local/bin/frpc`，配置写入 `/etc/frp/frpc.ini`。
- 创建 `/etc/systemd/system/frpc.service` 并启用开机自启。

## 2026-06-10 15:47:47 +0800 - RustDesk 开机自启

- RustDesk 安装完成后尝试执行 `systemctl enable --now rustdesk`。
- 如果安装包未提供 `rustdesk.service`，会提示警告但不阻断服务器配置和固定密码设置。

## 2026-06-10 15:47:47 +0800 - RustDesk 包选择优化

- RustDesk 安装工具优先选择 GitHub release 中当前架构对应的主线 `.deb` 包。
- 如果 release 中不存在非 `sciter` 的主线包，才回退使用 `sciter` 包。
- 这样可以避免在同时存在 Flutter 主线包和 Sciter 兼容包时，误装 `rustdesk-*-sciter.deb`。

## 2026-06-10 15:38:22 +0800 - 97172fc Set RustDesk permanent password

- RustDesk 安装完成后自动导入 ID/中继服务器配置。
- 自动设置固定密码，规则为：用户名首字母大写后拼接 `#2026`。
- 示例：`zzr` 对应密码 `Zzr#2026`。

## 2026-06-10 15:24:56 +0800 - 1b685eb Add RustDesk uninstall option

- 新增菜单项 `[6]`：卸载 RustDesk 并清理当前用户配置。
- 卸载流程包括 `apt remove`、`apt purge`、`apt autoremove` 和删除用户侧 RustDesk 配置目录。
- RustDesk 工具脚本通过菜单 `mode` 字段区分安装和卸载，避免复制两份脚本。

## 2026-06-10 15:20:43 +0800 - bd2b0c9 Add RustDesk installer

- 新增菜单项 `[5]`：安装并配置 RustDesk 远程控制。
- 自动识别 `amd64` / `arm64` 架构。
- 从 RustDesk GitHub 最新 release 查找对应 `.deb` 包并安装。
- 安装完成后导入预置 ID/中继服务器配置。

## 2026-06-10 09:37:46 +0800 - 7b85775 Document office installer testing and deployment

- README 增加异机测试说明。
- 补充局域网 HTTP、GitHub Raw、公网域名三种测试方式。
- 增加常见问题排查：默认域名、Raw 访问、局域网端口、sudo、apt 源等。

## 2026-06-10 09:25:43 +0800 - 0e86b8f Start office installer migration

- 将原 FishROS 安装器入口改造为办公软件安装器入口。
- 引入 `INSTALL_BASE_URL` 和 `/tmp/office_install`。
- 精简菜单，保留基础工具、微信、QQ、VS Code 等初始项。
- 新增基础工具包安装项，用于验证完整动态下载和工具执行链路。
