# Office Install

自有办公软件与基础工具一键安装器。当前分支是 `office`，目标是在 Ubuntu / Debian 电脑上通过一个入口脚本拉起交互菜单，再按需下载安装工具脚本。

当前 `office` 分支已恢复 FishROS 原有工具入口，并在后面追加自有办公软件与基础工具：

- `[1]`-`[18]`：FishROS 原有 ROS、Docker、系统源、开发工具、AI 工具等入口。
- `[19]`：基础工具包，用于测试安装器链路。
- `[20]` 以后：自有办公、网络与常用软件增强工具。

基础工具包内容：

```text
ca-certificates curl wget git unzip xz-utils
```

当前已新增 RustDesk 菜单项：

```text
[20]: 一键安装并配置 RustDesk 远程控制
[21]: 一键卸载 RustDesk 远程控制
```

RustDesk 工具会从 GitHub 最新 release 下载当前架构对应的主线 `.deb` 安装包，安装完成后自动导入预置 ID/中继服务器配置、启用 systemd 开机自启，并设置固定密码。密码规则为：用户名首字母大写后拼接 `#2026`，例如用户 `zzr` 的密码为 `Zzr#2026`。

当前已新增 frpc 菜单项：

```text
[22]: 一键安装并配置 frpc SSH 内网穿透
```

frpc 工具会连接 `frpc.jtcx.cn:7000`，把本机 `127.0.0.1:22` 映射到远端 TCP 端口。远端端口从 `2500` 开始探测，如果端口已被占用则顺延递增，最大尝试到 `2599`。安装完成后会写入 `/etc/frp/frpc.ini` 和 `/etc/systemd/system/frpc.service`，并执行 `systemctl enable --now frpc` 设置开机自启。

当前已新增搜狗输入法菜单项：

```text
[23]: 一键安装并配置 搜狗输入法
```

搜狗输入法工具会从搜狗 Linux 官方页面解析当前架构对应的 `.deb` 下载地址，安装 fcitx 相关依赖，并为当前用户写入 fcitx 输入法环境变量。安装完成后通常需要注销并重新登录。

当前已新增终端环境菜单项：

```text
[24]: 一键安装并配置 Zellij 终端复用器
[25]: 一键安装并配置 Oh My Zsh
```

Zellij 工具会从 GitHub 最新 release 下载当前架构安装包，写入默认 `~/.config/zellij/config.kdl`，启用滚轮查看历史输出、选择文本复制到系统剪贴板，并默认使用兼容字符配置，避免缺少 Nerd Font/Powerline 字体时 Tab 标签显示乱码。

Oh My Zsh 工具会安装 zsh、git、Powerline 字体，克隆 Oh My Zsh 官方框架和常用插件，并写入默认 `.zshrc`。

当前已新增 Chrome 菜单项：

```text
[26]: 一键安装 Google Chrome 最新版
```

Chrome 工具会从 Google 官方 Linux 直链下载当前稳定版 `google-chrome-stable_current_amd64.deb` 并通过 apt 安装。当前仅支持 `amd64` 架构。

当前已新增 AI 编程助手菜单项：

```text
[27]: 一键安装/卸载 AI 编程助手(Codex/Claude Code/Copilot)
```

AI 编程助手工具会通过官方 npm 包安装 OpenAI Codex CLI、Claude Code 和 GitHub Copilot CLI，支持单独安装、全部安装和卸载。安装前会检查 Node.js 版本，Copilot CLI 需要 Node.js 22+，Codex/Claude Code 需要 Node.js 18+；不满足时会调用 Node.js 安装器升级到当前最新 LTS。安装完成后需要按各工具提示登录对应账号：`codex`、`claude`、`copilot`。

当前已新增办公套件菜单项：

```text
[28]: 一键安装 办公套件(Zotero/Obsidian/WPS/字体)
```

办公套件工具支持安装 Zotero、Obsidian、WPS Office，以及中文字体和 Windows 常用字体。Zotero 使用官方 Linux tarball 安装到 `/opt/zotero`；Obsidian 从 GitHub 最新 release 选择当前架构 deb；WPS 从 WPS Linux 官方页面解析当前 amd64 deb。字体安装包括 Noto CJK、文泉驿、AR PL 中文字体、Liberation、Carlito/Caladea，尝试安装 `ttf-mscorefonts-installer`，并写入常见 Windows/Office 字体名替换规则；在发现 `/mnt/c/Windows/Fonts`、`/mnt/*/Windows/Fonts`、`/media/<user>/*/Windows/Fonts`、`/run/media/<user>/*/Windows/Fonts` 或 `WINDOWS_FONTS_DIR` 指定目录时导入本机 Windows 字体到当前用户字体目录。

## 版本策略

FishROS 原工具中部分软件曾固定到特定下载包，主要是为了当时的可复现性、下载源稳定性和兼容旧系统。当前 `office` 分支对常用桌面/开发软件优先采用稳定版最新发布：

- VS Code：使用 Microsoft stable 最新下载端点。
- Node.js：默认动态选择当前最新 LTS 主版本，保留 22/20 等兼容选项。
- Docker：使用 Docker CE stable apt 仓库，安装仓库中的最新版。
- 微信：默认选择官方 Linux 最新版，Docker 版和旧桌面版作为兼容备选。
- Chrome：使用 Google Chrome stable 官方最新版 deb。

下载行为：入口脚本、运行时文件、菜单工具脚本和当前菜单中的软件安装包都会在终端显示下载地址、进度条和实时速度，便于判断网络是否正常。

## 工作方式

入口脚本只做几件事：

1. 创建临时目录 `/tmp/office_install`。
2. 从 `INSTALL_BASE_URL` 下载 `install.py`。
3. 安装 Python 运行依赖 `python3-distro`、`python3-yaml`。
4. 执行 `/tmp/office_install/install.py`。
5. Python 主程序再按需下载 `tools/base.py`、翻译文件和用户选择的工具脚本。

默认下载根地址是：

```bash
https://install.example.com/
```

实际测试或部署时应通过环境变量覆盖：

```bash
INSTALL_BASE_URL=http://your-server:18080/
```

## 在其他电脑测试验证

### 方式一：同一局域网内测试

在开发电脑或 NAS 上进入项目目录并启动静态 HTTP 服务：

```bash
cd /home/slam/Project/install
python3 -m http.server 18080
```

确认测试电脑能访问该服务。假设服务电脑 IP 是 `192.168.1.10`，在测试电脑上运行：

```bash
wget --no-proxy -O /tmp/office-install http://192.168.1.10:18080/install && INSTALL_BASE_URL=http://192.168.1.10:18080/ bash /tmp/office-install
```

如果测试电脑开启了 Clash、系统代理或 TUN，访问局域网安装器时建议显式绕过代理。假设服务电脑 IP 是 `192.168.5.218`：

```bash
no_proxy=192.168.5.218,127.0.0.1,localhost NO_PROXY=192.168.5.218,127.0.0.1,localhost bash -c 'wget --no-proxy -O /tmp/office-install http://192.168.5.218:18080/install && INSTALL_BASE_URL=http://192.168.5.218:18080/ bash /tmp/office-install'
```

进入菜单后选择 `19`，测试基础工具包安装链路。

测试电脑要求：

- Ubuntu / Debian 系统。
- 能访问部署安装器的 HTTP 地址。
- 当前用户可以使用 `sudo`。
- 系统 apt 源可用。

### 方式二：直接用 GitHub Raw 测试

如果 `office` 分支已经推送到 GitHub，可以在测试电脑上运行：

```bash
wget -O /tmp/office-install https://raw.githubusercontent.com/WingBot/install/office/install && INSTALL_BASE_URL=https://raw.githubusercontent.com/WingBot/install/office/ bash /tmp/office-install
```

这种方式适合快速验证 GitHub 上的当前分支，但测试电脑需要能访问 GitHub Raw。

### 方式三：用公网域名测试

当前公网入口推荐使用一行命令：

```bash
no_proxy=install.todobot.org,156.239.236.24,127.0.0.1,localhost NO_PROXY=install.todobot.org,156.239.236.24,127.0.0.1,localhost bash -c 'wget --no-proxy -O /tmp/office-install http://install.todobot.org:8080/install && INSTALL_BASE_URL=http://install.todobot.org:8080/ bash /tmp/office-install'
```

如果测试电脑没有开启系统代理，也可以使用更短版本：

```bash
wget -O /tmp/office-install http://install.todobot.org:8080/install && INSTALL_BASE_URL=http://install.todobot.org:8080/ bash /tmp/office-install
```

公网服务器、HTTPS、安装器静态分发、GitHub 反向代理和软件包缓存的完整部署步骤见：[公网服务器部署指引](DEPLOY_PUBLIC_SERVER.md)。

## 安装器 HTTP 服务和软件源的关系

本项目里的 HTTP 服务只负责托管安装器文件，例如：

```text
install
install.py
tools/base.py
tools/tool_install_basic_tools.py
tools/translation/translator.py
tools/translation/assets/zh_CN.py
tools/translation/assets/en_US.py
```

它默认不托管要安装的软件包，也不自动替代系统软件源。

也就是说：

- `INSTALL_BASE_URL` 是安装器脚本根地址。
- `apt install` 仍然访问目标电脑配置的 apt 软件源。
- 如果某个工具脚本下载 `.deb`、压缩包或访问软件官网，那么访问地址由该工具脚本决定。

如果测试电脑访问国外网站较慢，可以按下面几种方式处理：

1. 使用国内 apt 源：在测试电脑上提前配置清华、阿里云、中科大等 Ubuntu/Debian 镜像源。
2. 在工具脚本中优先使用国内可访问的官方镜像或可信镜像。
3. 在内网服务器或 NAS 上缓存 `.deb`、压缩包等安装文件，然后让工具脚本下载内网地址。
4. 在网络环境中配置 HTTP/HTTPS 代理，并让工具脚本或 apt 使用代理。
5. 后续新增一个“配置系统源/代理”的菜单项，在安装办公软件前先完成网络配置。

不要把 `INSTALL_BASE_URL` 理解成“所有软件包的镜像源”。它只是安装器自身的脚本分发地址。是否托管第三方软件包，需要每个工具脚本单独设计。

## 部署在 NAS 时的访问权限问题

NAS 只需要对测试电脑提供只读 HTTP 访问。测试电脑通过 `wget` 下载脚本，不需要写入 NAS。

常见部署方式：

### 局域网公开只读

适合内网测试。NAS 上启动静态文件服务，让同一局域网电脑访问：

```bash
cd /path/to/install
python3 -m http.server 18080
```

然后测试电脑通过 `http://NAS_IP:18080/` 访问。注意 NAS 文件权限要允许运行 HTTP 服务的用户读取项目文件。

### 公网 HTTPS 访问

适合外部电脑测试。推荐结构：

```text
测试电脑
  |
  | HTTPS
  v
公网服务器 / Nginx 或 Caddy
  |
  | frp / VPN / 内网穿透
  v
NAS 静态文件服务
```

公网入口建议使用 HTTPS，不建议直接暴露 NAS 管理端口。

### 私有访问控制

如果不想公开安装器文件，可以选择：

- 只允许局域网、VPN、Tailscale、WireGuard 内访问。
- 在 Nginx/Caddy 上做 IP 白名单。
- 使用带时效的签名 URL。
- 使用 Basic Auth，但当前入口脚本还没有内置账号密码参数，需要额外改造 `wget` 命令。

不建议把 GitHub Token、NAS 密码或长期有效的私有下载凭据写死在 `install` 脚本中，因为测试电脑上可以直接看到这些内容。

如果部署在私有 GitHub 仓库，测试电脑下载 Raw 文件通常需要认证。为了简化测试，建议把安装器脚本部署到可控的内网 HTTP 服务，或者只公开 `office` 分支中的安装器脚本文件。

## 异机常见问题

### 默认域名无法访问

如果测试电脑上直接运行 `bash install`，入口脚本会使用默认地址：

```bash
https://install.example.com/
```

这个地址目前只是占位域名，没有部署真实服务时会下载失败。异机测试必须显式指定 `INSTALL_BASE_URL`：

```bash
INSTALL_BASE_URL=http://192.168.1.10:18080/ bash /tmp/office-install
```

或者使用 GitHub Raw：

```bash
INSTALL_BASE_URL=https://raw.githubusercontent.com/WingBot/install/office/ bash /tmp/office-install
```

### GitHub Raw 下载失败

如果看到 `raw.githubusercontent.com` 连接失败、超时或 404，按下面顺序检查：

1. 确认 `office` 分支已经推送到 GitHub。
2. 确认测试电脑能访问 `https://raw.githubusercontent.com/WingBot/install/office/install`。
3. 如果仓库是私有仓库，Raw 地址通常需要认证；建议改用内网 HTTP 服务或公网 HTTPS 服务测试。
4. 如果网络无法访问 GitHub Raw，改用局域网方式：在开发电脑启动 `python3 -m http.server 18080`。

### 局域网 HTTP 服务无法访问

如果测试电脑访问 `http://192.168.1.10:18080/install` 失败：

1. 确认服务端正在项目根目录运行 `python3 -m http.server 18080`。
2. 确认 IP 地址是服务端的局域网 IP，不是 `127.0.0.1`。
3. 在测试电脑浏览器或命令行访问：

```bash
wget -S --spider http://192.168.1.10:18080/install
```

4. 检查服务端防火墙是否放行 18080 端口。
5. 确认两台电脑在同一局域网，或者路由/VPN 已经打通。

### sudo 权限问题

第 19 项基础工具包会执行 apt 安装，需要 sudo 权限。如果看到类似：

```text
sudo: a password is required
当前会话无法无交互使用 sudo
```

说明当前运行环境不能交互输入 sudo 密码。请在测试电脑的真实终端里运行安装器，不要在无法输入密码的后台任务里运行。正常情况下选择菜单项后输入当前用户的 sudo 密码即可。

### Zellij Tab 标签乱码

如果 Zellij 顶部 `Tab #1` 标签前后出现乱码，通常是终端字体缺少 Nerd Font/Powerline 符号。最新安装器默认写入兼容字符配置；已经安装过的电脑可以重新运行菜单 `[24]`，安装器会备份旧配置并重写 `~/.config/zellij/config.kdl`。

也可以手动修改：

```bash
sed -i 's/^simplified_ui .*/simplified_ui true/; s/^pane_frames .*/pane_frames false/' ~/.config/zellij/config.kdl
```

然后退出并重新进入 `zellij`。

### 开启代理后局域网地址被代理

如果测试电脑开启了 Clash 系统代理或 TUN，`wget http://192.168.x.x:18080/install` 可能会被送进代理，表现为连接 `127.0.0.1:7897` 后返回 `502 Bad Gateway`。这种情况下使用下面的一行命令，让下载入口和安装器内部下载都显式走 `no_proxy/NO_PROXY`：

```bash
no_proxy=192.168.5.218,127.0.0.1,localhost NO_PROXY=192.168.5.218,127.0.0.1,localhost bash -c 'wget --no-proxy -O /tmp/office-install http://192.168.5.218:18080/install && INSTALL_BASE_URL=http://192.168.5.218:18080/ bash /tmp/office-install'
```

如果服务端 IP 不是 `192.168.5.218`，把命令里的 IP 全部替换成实际服务端 IP。

### 搜狗输入法安装后不能输入中文

如果搜狗输入法已经安装，`fcitx` 配置里也能添加搜狗，但重启后仍不能输入中文，先确认会话是否真的由 `fcitx` 接管：

```bash
echo $XDG_SESSION_TYPE
echo $GTK_IM_MODULE
echo $QT_IM_MODULE
echo $XMODIFIERS
pgrep -a fcitx
im-config -m
cat ~/.xinputrc 2>/dev/null
```

如果输出类似下面这样，说明 X11、环境变量和 `fcitx` 进程基本正常：

```text
x11
fcitx
fcitx
@im=fcitx
/usr/bin/fcitx -r
```

这种情况下重点排查搜狗引擎是否加载成功、当前输入法是否切到搜狗，以及 `ibus` 是否仍在竞争：

```bash
fcitx-remote -n
fcitx-diagnose | tee /tmp/fcitx-diagnose.log
dpkg -l | grep -E 'sogoupinyin|fcitx|ibus'
ls /usr/share/fcitx/addon | grep -i sogou
pgrep -a ibus
```

处理建议：

1. 重新运行菜单 `[23]`，新版安装器会写入 `~/.xinputrc` 为 `run_im fcitx`，并增加 `~/.config/autostart/fcitx.desktop`。
2. 注销并重新登录，不只是在终端里重开 shell。
3. 打开 `fcitx-config-gtk3`，确认输入法列表里有“搜狗拼音”，并把它放在列表中；测试时用 `Ctrl+Space` 或配置里的切换键切到搜狗。
4. 如果 `pgrep -a ibus` 仍有进程，可临时执行 `ibus exit` 后再测试。
5. 如果 `fcitx-diagnose` 里搜狗 addon 加载失败，问题通常是搜狗 `.deb` 与当前 Ubuntu/Debian 版本或 Qt 依赖不兼容，需要根据诊断日志继续处理。

如果是 Wayland 会话且无法输入，优先在登录界面切换到 `Ubuntu on Xorg` 后再测试。

### apt 源或网络问题

如果工具脚本已经启动，但 `sudo apt update` 或 `sudo apt install` 失败，问题通常不在 `INSTALL_BASE_URL`，而在测试电脑自己的 apt 源或网络：

1. 先手动执行：

```bash
sudo apt update
```

2. 如果 apt 源慢或不可达，先切换到可用镜像源。
3. 如果公司/校园网络需要代理，先配置系统代理或 apt 代理。
4. 再重新运行安装器选择第 1 项。

### 快速判断问题位置

- 下载 `/tmp/office-install` 失败：入口脚本地址不可达。
- 下载 `install.py`、`tools/base.py` 失败：`INSTALL_BASE_URL` 配错或服务不可达。
- 菜单能出现，但工具脚本下载失败：服务目录缺少对应 `tools/tool_install_xxx.py`。
- 工具脚本已启动，但 apt 失败：测试电脑 apt 源、sudo 或系统网络问题。

## 自动选择测试

可以用配置文件自动选择菜单项，便于链路测试。

自动选择退出：

```bash
cat > /tmp/office_install_choose_exit.yaml <<'EOF'
chooses:
- choose: 0
  desc: quit
time: test
EOF

OFFICE_INSTALL_CONFIG=/tmp/office_install_choose_exit.yaml INSTALL_BASE_URL=http://127.0.0.1:18080/ python3 install.py
```

自动选择第 19 项基础工具包：

```bash
cat > /tmp/office_install_choose_basic.yaml <<'EOF'
chooses:
- choose: 19
  desc: basic tools
time: test
EOF

OFFICE_INSTALL_CONFIG=/tmp/office_install_choose_basic.yaml INSTALL_BASE_URL=http://127.0.0.1:18080/ python3 install.py
```

真实安装基础工具包需要当前用户可以使用 `sudo`。

## 后续计划

- 确认真实 `INSTALL_BASE_URL` 域名。
- 增加 WPS、飞书、frpc 等办公和网络工具。
- 增加系统源和代理配置菜单。
- 设计内网缓存包或镜像源方案。
