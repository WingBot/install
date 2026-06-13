# 公网服务器部署指引

本文说明如何把本项目部署到有公网 IP 和域名的云服务器上。推荐分两阶段推进：

1. 第一阶段：只部署安装器入口和脚本静态站点，让测试电脑不依赖系统代理即可打开安装器；Clash/代理工具安装包沿用当前 FishROS 风格的 `repo.trojan-cdn.com` 下载源。安装 Clash 后，开启系统代理，再继续安装需要 GitHub 的工具。
2. 第二阶段：再增加 GitHub 反向代理和自托管软件包缓存，让 GitHub Raw、GitHub Release、大文件安装包也能通过自己的域名中转。

这样可以先跑通最短链路，避免一开始同时处理 HTTPS、反向代理、安全限制、包缓存等多个变量。

示例域名：

```text
install.example.com      第一阶段：安装器静态文件
github.example.com       第二阶段：GitHub 反向代理
pkg.example.com          第二阶段：自托管软件包缓存
```

实际部署时把示例域名替换为自己的域名。

## 总体目标结构

推荐把“安装器脚本分发”和“第三方下载中转”分开。第一阶段只实现 `install.example.com`；第二阶段再实现 `github.example.com` 和 `pkg.example.com`。

```text
测试电脑
  |
  | HTTPS
  v
install.example.com
  |-- /install
  |-- /install.py
  |-- /tools/base.py
  |-- /tools/tool_*.py

github.example.com
  |-- /https://raw.githubusercontent.com/...
  |-- /https://github.com/.../releases/download/...

pkg.example.com
  |-- /packages/*.deb
  |-- /packages/*.tar.gz
```

其中：

- `install.example.com` 只托管本项目文件，供 `INSTALL_BASE_URL` 使用。
- `github.example.com` 作为 GitHub Raw/Release 的反向代理，解决测试电脑直连 GitHub 不稳定的问题。
- `pkg.example.com` 用来放体积较大的固定软件包，例如 `.deb`、`.tar.gz`，避免每次都从国外源下载。

## 阶段选择

### 第一阶段先做什么

第一阶段只要求：

- 域名 `install.example.com` 指向云服务器。
- Nginx 能托管本项目文件。
- 测试电脑能运行 `wget https://install.example.com/install`。
- 进入安装器后能选择“科学上网代理工具”，下载并安装 Clash Verge Rev 或 mihomo-party。

当前代理工具安装脚本的包地址是：

```text
https://repo.trojan-cdn.com/clash-verge-rev/...
https://repo.trojan-cdn.com/mihomo-party/...
```

这类下载源不依赖 GitHub。安装完成后，导入订阅、开启系统代理或 TUN，再继续运行安装器。项目中 RustDesk、frpc、Zellij、Obsidian 等工具已经有本地代理检测逻辑，检测到 `127.0.0.1:7897` 或环境变量代理后会优先使用代理下载 GitHub 资源。

第一阶段推荐客户端流程：

```bash
wget -O /tmp/office-install https://install.example.com/install
INSTALL_BASE_URL=https://install.example.com/ bash /tmp/office-install
```

然后在菜单中选择：

```text
[14] 一键安装:科学上网代理工具
```

Clash 安装并配置好后，再重新执行安装器安装其他工具。

### 第二阶段再做什么

第二阶段再补：

- `github.example.com`：GitHub Raw / GitHub Release 中转。
- `pkg.example.com`：自托管固定安装包缓存。
- 工具脚本中的 GitHub 下载 URL 可以逐步改成优先走中转，失败再回源。

这样即使目标电脑没有系统代理，也能通过你的云服务器中转一部分 GitHub 下载。

## 第一阶段：DNS 配置

在域名服务商处增加 A 记录：

```text
install.example.com  A  你的公网服务器 IP
```

等待解析生效后，在本地或服务器上检查：

```bash
dig +short install.example.com
```

如果测试电脑开启 Clash TUN 并看到 `198.18.x.x`，这是 Clash fake-ip，不代表真实服务器 IP。用浏览器或 `curl -I` 看 HTTP 响应更可靠。

第二阶段再增加：

```text
github.example.com   A  你的公网服务器 IP
pkg.example.com      A  你的公网服务器 IP
```

## 第一阶段：服务器准备

以下命令以 Ubuntu/Debian 云服务器为例：

```bash
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx git rsync
```

创建目录：

```bash
sudo mkdir -p /srv/office-install
sudo chown -R "$USER":"$USER" /srv/office-install
```

开放安全组和防火墙：

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

云厂商控制台也要放行 80 和 443。

## 第一阶段：同步项目文件

方式一：服务器直接拉 GitHub 仓库。

```bash
cd /srv
git clone -b office https://github.com/WingBot/install.git office-install
```

后续更新：

```bash
cd /srv/office-install
git pull --ff-only
```

方式二：从开发电脑同步到服务器。

```bash
rsync -av --delete \
  --exclude '.git' \
  --exclude '__pycache__' \
  /home/slam/Project/install/ \
  user@your-server:/srv/office-install/
```

## 第一阶段：配置安装器静态站点

新建 Nginx 配置：

```bash
sudo tee /etc/nginx/sites-available/office-install >/dev/null <<'EOF'
server {
    listen 80;
    server_name install.example.com;

    root /srv/office-install;
    index index.html;

    charset utf-8;

    location / {
        try_files $uri =404;
    }

    location ~ /\. {
        deny all;
    }

    location ~* \.(py|sh|yaml|md|txt|json)$ {
        add_header Cache-Control "no-cache";
        try_files $uri =404;
    }
}
EOF
```

启用站点：

```bash
sudo ln -sf /etc/nginx/sites-available/office-install /etc/nginx/sites-enabled/office-install
sudo nginx -t
sudo systemctl reload nginx
```

测试：

```bash
curl -I http://install.example.com/install
curl -I http://install.example.com/install.py
curl -I http://install.example.com/tools/base.py
```

测试电脑运行：

```bash
wget -O /tmp/office-install http://install.example.com/install
INSTALL_BASE_URL=http://install.example.com/ bash /tmp/office-install
```

## 第一阶段：配置 HTTPS

申请证书：

```bash
sudo certbot --nginx -d install.example.com
```

验证自动续期：

```bash
sudo certbot renew --dry-run
```

HTTPS 可用后，测试电脑运行：

```bash
wget -O /tmp/office-install https://install.example.com/install
INSTALL_BASE_URL=https://install.example.com/ bash /tmp/office-install
```

如果希望像 FishROS 一样入口脚本默认就使用自己的域名，可以修改项目根目录 `install` 中的默认值：

```bash
export INSTALL_BASE_URL="${INSTALL_BASE_URL:-https://install.example.com/}"
```

这样测试电脑可直接运行：

```bash
wget -O /tmp/office-install https://install.example.com/install && bash /tmp/office-install
```

## 第一阶段：安装 Clash 并开启代理

第一阶段不强制配置 GitHub 中转。先使用当前菜单中的代理工具安装入口：

```text
[14] 一键安装:科学上网代理工具
```

当前脚本提供两个选项：

```text
1. 有界面版: Clash Verge Rev
2. 无界面版(按提供源): mihomo-party
```

安装包下载源沿用 FishROS 风格的独立下载域名：

```text
https://repo.trojan-cdn.com/clash-verge-rev/...
https://repo.trojan-cdn.com/mihomo-party/...
```

安装完成后：

1. 启动 Clash Verge Rev 或 mihomo-party。
2. 导入订阅。
3. 开启系统代理或 TUN。
4. 如需终端显式代理，执行安装器写入的快捷命令：

```bash
source ~/.bashrc
proxy_add
proxy_status
```

后续再运行安装器：

```bash
wget -O /tmp/office-install https://install.example.com/install
INSTALL_BASE_URL=https://install.example.com/ bash /tmp/office-install
```

此时需要访问 GitHub 的 Python 下载工具会优先读取 `http_proxy`、`https_proxy`、`all_proxy`，或自动检测本地 `127.0.0.1:7897` 代理。

## 第二阶段：配置 GitHub 反向代理

### 基本原理

让测试电脑访问：

```text
https://github.example.com/https://raw.githubusercontent.com/WingBot/install/office/install
```

Nginx 收到请求后，把路径中的真实 URL 解出来，再由服务器去请求 GitHub，并把结果返回给测试电脑。

这类服务等价于下载中转。它不需要测试电脑有系统代理，但要求云服务器自己能访问 GitHub。

### 推荐方案：Nginx + Python 中转服务

纯 Nginx 动态代理任意完整 URL 配置复杂，也容易产生安全问题。推荐用一个很小的本地 Python 服务负责白名单校验和下载，再由 Nginx 暴露 HTTPS。

创建服务目录：

```bash
sudo mkdir -p /opt/office-github-proxy
sudo chown -R "$USER":"$USER" /opt/office-github-proxy
```

创建 `/opt/office-github-proxy/proxy.py`：

```python
#!/usr/bin/env python3
import urllib.parse
import urllib.request
import ipaddress
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ALLOWED_HOSTS = {
    "github.com",
    "raw.githubusercontent.com",
    "api.github.com",
    "objects.githubusercontent.com",
    "release-assets.githubusercontent.com",
}

MAX_BYTES = 1024 * 1024 * 1024


def host_is_public(hostname):
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False
    for info in infos:
        address = info[4][0]
        ip = ipaddress.ip_address(address)
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
        ):
            return False
    return True


class Handler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.proxy(send_body=False)

    def do_GET(self):
        self.proxy(send_body=True)

    def proxy(self, send_body=True):
        target = urllib.parse.unquote(self.path.lstrip("/"))
        if not target.startswith(("https://", "http://")):
            self.send_error(400, "path must be a full URL")
            return

        parsed = urllib.parse.urlparse(target)
        if parsed.hostname not in ALLOWED_HOSTS:
            self.send_error(403, "host is not allowed")
            return
        if not host_is_public(parsed.hostname):
            self.send_error(403, "resolved address is not public")
            return

        request = urllib.request.Request(
            target,
            headers={
                "User-Agent": "office-install-github-proxy/1.0",
                "Accept": "*/*",
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                length = response.headers.get("Content-Length")
                if length and int(length) > MAX_BYTES:
                    self.send_error(413, "file too large")
                    return

                self.send_response(response.status)
                for key, value in response.headers.items():
                    key_lower = key.lower()
                    if key_lower in {"transfer-encoding", "connection", "content-encoding"}:
                        continue
                    self.send_header(key, value)
                self.end_headers()

                if not send_body:
                    return

                copied = 0
                while True:
                    chunk = response.read(1024 * 256)
                    if not chunk:
                        break
                    copied += len(chunk)
                    if copied > MAX_BYTES:
                        break
                    self.wfile.write(chunk)
        except Exception as exc:
            self.send_error(502, str(exc))


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 18081), Handler).serve_forever()
```

创建 systemd 服务：

```bash
sudo tee /etc/systemd/system/office-github-proxy.service >/dev/null <<'EOF'
[Unit]
Description=Office Install GitHub Proxy
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /opt/office-github-proxy/proxy.py
Restart=always
RestartSec=3
User=www-data
Group=www-data

[Install]
WantedBy=multi-user.target
EOF
```

启动：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now office-github-proxy
sudo systemctl status office-github-proxy
```

Nginx 配置：

```bash
sudo tee /etc/nginx/sites-available/office-github-proxy >/dev/null <<'EOF'
server {
    listen 80;
    server_name github.example.com;

    client_max_body_size 1024m;
    proxy_read_timeout 300s;
    proxy_send_timeout 300s;

    location / {
        proxy_pass http://127.0.0.1:18081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_buffering off;
    }
}
EOF
```

启用并申请证书：

```bash
sudo ln -sf /etc/nginx/sites-available/office-github-proxy /etc/nginx/sites-enabled/office-github-proxy
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d github.example.com
```

测试：

```bash
curl -I "https://github.example.com/https://raw.githubusercontent.com/WingBot/install/office/install"
```

下载测试：

```bash
wget -O /tmp/office-install "https://github.example.com/https://raw.githubusercontent.com/WingBot/install/office/install"
```

### 在工具脚本里使用中转地址

对 GitHub Raw：

```text
https://raw.githubusercontent.com/WingBot/install/office/install
```

改成：

```text
https://github.example.com/https://raw.githubusercontent.com/WingBot/install/office/install
```

对 GitHub Release：

```text
https://github.com/fatedier/frp/releases/download/v0.69.1/frp_0.69.1_linux_amd64.tar.gz
```

改成：

```text
https://github.example.com/https://github.com/fatedier/frp/releases/download/v0.69.1/frp_0.69.1_linux_amd64.tar.gz
```

注意：GitHub Release 经常 302 跳转到 `release-assets.githubusercontent.com`。上面的 Python 中转会跟随跳转，测试电脑只需要访问你的 `github.example.com`。

## 第二阶段：配置软件包缓存站点

如果某些安装包经常用、体积大或源站不稳定，建议直接缓存到自己的服务器。

Nginx 配置：

```bash
sudo tee /etc/nginx/sites-available/office-packages >/dev/null <<'EOF'
server {
    listen 80;
    server_name pkg.example.com;

    root /srv/office-packages;
    autoindex off;
    client_max_body_size 1024m;

    location / {
        try_files $uri =404;
    }

    location ~ /\. {
        deny all;
    }
}
EOF
```

启用并申请证书：

```bash
sudo ln -sf /etc/nginx/sites-available/office-packages /etc/nginx/sites-enabled/office-packages
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d pkg.example.com
```

上传或下载缓存包：

```bash
cd /srv/office-packages/packages
wget -O google-chrome-stable_current_amd64.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
```

测试：

```bash
curl -I https://pkg.example.com/packages/google-chrome-stable_current_amd64.deb
```

工具脚本中可优先使用：

```text
https://pkg.example.com/packages/google-chrome-stable_current_amd64.deb
```

源站作为 fallback。这样最稳定，也最容易排查。

## 客户端验证命令

第一阶段基础验证：

```bash
wget -O /tmp/office-install https://install.example.com/install
INSTALL_BASE_URL=https://install.example.com/ bash /tmp/office-install
```

如果客户端已经开启 Clash/TUN，访问公网域名通常不需要 `no_proxy`。只有访问局域网 IP 时才需要显式绕过代理。

第二阶段验证 GitHub 中转：

```bash
wget -O /tmp/office-install "https://github.example.com/https://raw.githubusercontent.com/WingBot/install/office/install"
```

第二阶段验证大文件中转：

```bash
wget -O /tmp/frp.tar.gz "https://github.example.com/https://github.com/fatedier/frp/releases/download/v0.69.1/frp_0.69.1_linux_amd64.tar.gz"
```

第二阶段验证自托管包：

```bash
wget -O /tmp/test.deb https://pkg.example.com/packages/google-chrome-stable_current_amd64.deb
```

## 安全注意事项

不要开放任意 URL 代理。反向代理必须至少做这些限制：

- 只允许代理 `github.com`、`raw.githubusercontent.com`、`api.github.com`、`release-assets.githubusercontent.com` 等明确域名。
- 限制单文件最大体积。
- 不代理内网地址、云服务器 metadata 地址、本机地址。
- 不允许 POST/PUT/DELETE，只开放 GET/HEAD。
- Nginx 和 systemd 日志要保留，便于定位滥用或失败原因。

如果只是为了稳定安装，优先使用 `pkg.example.com` 缓存固定安装包；GitHub 反向代理只作为动态 release、Raw 文件的补充。

## 排查

查看 Nginx 配置：

```bash
sudo nginx -t
sudo systemctl status nginx
```

查看 GitHub 中转服务：

```bash
sudo systemctl status office-github-proxy
sudo journalctl -u office-github-proxy -n 100 --no-pager
```

服务器能否访问 GitHub：

```bash
curl -I https://github.com
curl -I https://raw.githubusercontent.com/WingBot/install/office/install
```

客户端能否访问你的域名：

```bash
curl -I https://install.example.com/install
curl -I "https://github.example.com/https://raw.githubusercontent.com/WingBot/install/office/install"
```

常见问题：

- `404`：路径不对，或 `/srv/office-install` 没有同步对应文件。
- `502`：GitHub 中转服务没启动，或服务器访问 GitHub 失败。
- `413`：文件超过 `MAX_BYTES` 或 Nginx `client_max_body_size` 限制。
- `SSL` 失败：证书未签发、域名未解析到当前服务器、80/443 未放行。
- 客户端仍走 Clash：公网域名通常可以走代理；如果代理失败，临时设置 `https_proxy=`、`http_proxy=` 后重试。
