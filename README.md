# Office Install

自有办公软件与基础工具一键安装器。当前分支是 `office`，目标是在 Ubuntu / Debian 电脑上通过一个入口脚本拉起交互菜单，再按需下载安装工具脚本。

当前第一阶段已经完成最小链路：

- 入口脚本：`install`
- 主程序：`install.py`
- 公共框架：`tools/base.py`
- 翻译模块：`tools/translation/translator.py`
- 第一个测试工具：`tools/tool_install_basic_tools.py`

当前菜单中第一个测试项是基础工具包：

```text
ca-certificates curl wget git unzip xz-utils
```

当前已新增 RustDesk 菜单项：

```text
[5]: 一键安装并配置 RustDesk 远程控制
```

RustDesk 工具会从 GitHub 最新 release 下载当前架构对应的 `.deb` 安装包，安装完成后自动导入预置 ID/中继服务器配置。

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
wget -O /tmp/office-install http://192.168.1.10:18080/install
INSTALL_BASE_URL=http://192.168.1.10:18080/ bash /tmp/office-install
```

进入菜单后选择 `1`，测试基础工具包安装链路。

测试电脑要求：

- Ubuntu / Debian 系统。
- 能访问部署安装器的 HTTP 地址。
- 当前用户可以使用 `sudo`。
- 系统 apt 源可用。

### 方式二：直接用 GitHub Raw 测试

如果 `office` 分支已经推送到 GitHub，可以在测试电脑上运行：

```bash
wget -O /tmp/office-install https://raw.githubusercontent.com/WingBot/install/office/install
INSTALL_BASE_URL=https://raw.githubusercontent.com/WingBot/install/office/ bash /tmp/office-install
```

这种方式适合快速验证 GitHub 上的当前分支，但测试电脑需要能访问 GitHub Raw。

### 方式三：用公网域名测试

当后续部署了真实域名，例如 `https://install.example.com/`，测试命令可以变成：

```bash
wget -O /tmp/office-install https://install.example.com/install && INSTALL_BASE_URL=https://install.example.com/ bash /tmp/office-install
```

如果入口脚本里的默认 `INSTALL_BASE_URL` 已经改成真实域名，也可以直接运行：

```bash
wget -O /tmp/office-install https://install.example.com/install && bash /tmp/office-install
```

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

第 1 项基础工具包会执行 apt 安装，需要 sudo 权限。如果看到类似：

```text
sudo: a password is required
当前会话无法无交互使用 sudo
```

说明当前运行环境不能交互输入 sudo 密码。请在测试电脑的真实终端里运行安装器，不要在无法输入密码的后台任务里运行。正常情况下选择菜单项后输入当前用户的 sudo 密码即可。

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

自动选择第 1 项基础工具包：

```bash
cat > /tmp/office_install_choose_basic.yaml <<'EOF'
chooses:
- choose: 1
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
