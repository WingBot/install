# -*- coding: utf-8 -*-
import json
import os
import socket
import tarfile
import urllib.request

from .base import BaseTool, CmdTask, PrintUtils, osarch


FRP_RELEASE_API = "https://api.github.com/repos/fatedier/frp/releases/latest"
FRP_SERVER_ADDR = "frpc.jtcx.cn"
FRP_SERVER_PORT = 7000
LOCAL_SSH_PORT = 22
REMOTE_PORT_START = 2500
REMOTE_PORT_END = 2599


class Tool(BaseTool):
    def __init__(self):
        self.name = "frpc SSH内网穿透"
        self.type = BaseTool.TYPE_INSTALL
        self.author = "WingBot"

    def _check_sudo(self):
        sudo_check = CmdTask("sudo -n true", 0).run()
        if sudo_check[0] != 0:
            PrintUtils.print_error("当前会话无法无交互使用 sudo，请在终端中运行安装器并输入 sudo 密码后重试。")
            return False
        return True

    def _target_user(self):
        username = os.environ.get("SUDO_USER") or os.environ.get("LOGNAME") or os.environ.get("USER") or "root"
        if username == "root":
            return "root"
        return username

    def _proxy_name(self):
        hostname = socket.gethostname().replace(".", "-").replace("_", "-")
        username = self._target_user().replace(".", "-").replace("_", "-")
        return "{}-{}-ssh".format(username, hostname)

    def _asset_arch_keyword(self):
        if osarch == "amd64":
            return "linux_amd64"
        if osarch == "arm64":
            return "linux_arm64"
        if osarch == "armhf":
            return "linux_arm"
        return None

    def _latest_frp_url(self):
        arch_keyword = self._asset_arch_keyword()
        if arch_keyword is None:
            PrintUtils.print_error("当前架构暂不支持自动安装 frpc: {}".format(osarch))
            return None

        PrintUtils.print_info("正在获取 frp 最新 release 信息...")
        try:
            with urllib.request.urlopen(FRP_RELEASE_API, timeout=20) as response:
                release = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            PrintUtils.print_error("获取 frp release 信息失败: {}".format(exc))
            return None

        for asset in release.get("assets", []):
            name = asset.get("name", "")
            url = asset.get("browser_download_url", "")
            if arch_keyword in name and name.endswith(".tar.gz") and url:
                PrintUtils.print_info("已选择 frp 安装包: {}".format(name))
                return url

        PrintUtils.print_error("未找到适合当前架构的 frp 安装包。")
        return None

    def _is_remote_port_used(self, port):
        try:
            with socket.create_connection((FRP_SERVER_ADDR, port), timeout=1.0):
                return True
        except (ConnectionRefusedError, TimeoutError, OSError):
            return False

    def _allocate_remote_port(self):
        for port in range(REMOTE_PORT_START, REMOTE_PORT_END + 1):
            if not self._is_remote_port_used(port):
                PrintUtils.print_success("已选择 frpc 远端端口: {}".format(port))
                return port
            PrintUtils.print_info("远端端口 {} 已占用，尝试下一个。".format(port))

        PrintUtils.print_error("{}-{} 范围内没有找到可用远端端口。".format(REMOTE_PORT_START, REMOTE_PORT_END))
        return None

    def _install_binary(self, url):
        archive_path = "/tmp/frp.tar.gz"
        extract_dir = "/tmp/frp_extract"
        CmdTask("rm -rf {} {}".format(archive_path, extract_dir), 0).run()
        download_result = CmdTask(
            "wget '{}' -O {} --no-check-certificate".format(url, archive_path), 0
        ).run()
        if download_result[0] != 0:
            PrintUtils.print_error("frp 安装包下载失败。")
            return False

        os.makedirs(extract_dir, exist_ok=True)
        try:
            with tarfile.open(archive_path, "r:gz") as tar:
                self._safe_extract(tar, extract_dir)
        except Exception as exc:
            PrintUtils.print_error("frp 安装包解压失败: {}".format(exc))
            return False

        frpc_path = None
        for root, _, files in os.walk(extract_dir):
            if "frpc" in files:
                frpc_path = os.path.join(root, "frpc")
                break
        if frpc_path is None:
            PrintUtils.print_error("安装包中未找到 frpc 二进制。")
            return False

        install_result = CmdTask("sudo install -m 0755 {} /usr/local/bin/frpc".format(frpc_path), 0).run()
        if install_result[0] != 0:
            PrintUtils.print_error("frpc 二进制安装失败。")
            return False
        return True

    def _write_config(self, remote_port):
        proxy_name = self._proxy_name()
        config = """[common]
server_addr = {server_addr}
server_port = {server_port}

[{proxy_name}]
type = tcp
local_ip = 127.0.0.1
local_port = {local_port}
remote_port = {remote_port}
""".format(
            server_addr=FRP_SERVER_ADDR,
            server_port=FRP_SERVER_PORT,
            proxy_name=proxy_name,
            local_port=LOCAL_SSH_PORT,
            remote_port=remote_port,
        )
        temp_config = "/tmp/frpc.ini"
        with open(temp_config, "w", encoding="utf-8") as f:
            f.write(config)

        CmdTask("sudo mkdir -p /etc/frp", 0).run()
        result = CmdTask("sudo install -m 0644 {} /etc/frp/frpc.ini".format(temp_config), 0).run()
        if result[0] != 0:
            PrintUtils.print_error("写入 /etc/frp/frpc.ini 失败。")
            return False
        PrintUtils.print_success("frpc 配置已写入 /etc/frp/frpc.ini，代理名: {}".format(proxy_name))
        return True

    def _write_service(self):
        user = self._target_user()
        service = """[Unit]
Description=frp Client Service
After=network-online.target
Wants=network-online.target

[Service]
User={user}
Type=simple
ExecStart=/usr/local/bin/frpc -c /etc/frp/frpc.ini
Restart=always
RestartSec=3s
KillMode=process
TimeoutStopSec=1

[Install]
WantedBy=multi-user.target
""".format(user=user)
        temp_service = "/tmp/frpc.service"
        with open(temp_service, "w", encoding="utf-8") as f:
            f.write(service)

        result = CmdTask("sudo install -m 0644 {} /etc/systemd/system/frpc.service".format(temp_service), 0).run()
        if result[0] != 0:
            PrintUtils.print_error("写入 frpc systemd 服务失败。")
            return False

        CmdTask("sudo systemctl daemon-reload", 0).run()
        enable_result = CmdTask("sudo systemctl enable --now frpc", 0).run()
        if enable_result[0] != 0:
            PrintUtils.print_error("frpc 服务启动失败，请检查 /etc/frp/frpc.ini 和 journalctl -u frpc。")
            return False
        return True

    def run(self):
        if not self._check_sudo():
            return False

        frp_url = self._latest_frp_url()
        if frp_url is None:
            return False

        remote_port = self._allocate_remote_port()
        if remote_port is None:
            return False

        if not self._install_binary(frp_url):
            return False
        if not self._write_config(remote_port):
            return False
        if not self._write_service():
            return False

        PrintUtils.print_success("frpc 已安装并设置开机自启。")
        PrintUtils.print_success("SSH 访问地址: ssh -p {} <user>@{}".format(remote_port, FRP_SERVER_ADDR))
        return True
