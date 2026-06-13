# -*- coding: utf-8 -*-
import json
import os
import pwd
import shlex
import socket
import sys
import tarfile
import time
import urllib.request

from .base import BaseTool, CmdTask, PrintUtils, osarch


ZELLIJ_RELEASE_API = "https://api.github.com/repos/zellij-org/zellij/releases/latest"


class Tool(BaseTool):
    def __init__(self):
        self.name = "Zellij终端复用器"
        self.type = BaseTool.TYPE_INSTALL
        self.author = "WingBot"

    def _check_sudo(self):
        sudo_check = CmdTask("sudo -n true", 0).run()
        if sudo_check[0] != 0:
            PrintUtils.print_error("当前会话无法无交互使用 sudo，请在终端中运行安装器并输入 sudo 密码后重试。")
            return False
        return True

    def _proxy_opener(self):
        proxies = {}
        http_proxy = os.environ.get("http_proxy") or os.environ.get("HTTP_PROXY")
        https_proxy = os.environ.get("https_proxy") or os.environ.get("HTTPS_PROXY")
        all_proxy = os.environ.get("all_proxy") or os.environ.get("ALL_PROXY")
        if http_proxy:
            proxies["http"] = http_proxy
        if https_proxy:
            proxies["https"] = https_proxy
        if all_proxy:
            proxies.setdefault("http", all_proxy)
            proxies.setdefault("https", all_proxy)

        if not proxies and self._local_proxy_available("127.0.0.1", 7897):
            proxy_url = "http://127.0.0.1:7897"
            proxies = {"http": proxy_url, "https": proxy_url}
            PrintUtils.print_info("检测到本地代理，下载将使用: {}".format(proxy_url))

        if proxies:
            return urllib.request.build_opener(urllib.request.ProxyHandler(proxies))
        return urllib.request.build_opener()

    def _local_proxy_available(self, host, port):
        try:
            with socket.create_connection((host, port), timeout=1.0) as conn:
                conn.settimeout(1.0)
                conn.sendall(
                    b"CONNECT github.com:443 HTTP/1.1\r\n"
                    b"Host: github.com:443\r\n"
                    b"Proxy-Connection: close\r\n\r\n"
                )
                response = conn.recv(128)
            return b" 200 " in response.split(b"\r\n", 1)[0]
        except OSError:
            return False

    def _target_user(self):
        username = os.environ.get("SUDO_USER") or os.environ.get("LOGNAME") or os.environ.get("USER") or "root"
        if username == "root":
            return "root", "/root"
        try:
            info = pwd.getpwnam(username)
            return username, info.pw_dir
        except KeyError:
            return username, os.path.expanduser("~" + username)

    def _asset_keywords(self):
        if osarch == "amd64":
            return ["x86_64-unknown-linux-musl", "x86_64-unknown-linux-gnu"]
        if osarch == "arm64":
            return ["aarch64-unknown-linux-musl", "aarch64-unknown-linux-gnu"]
        return []

    def _latest_zellij_url(self):
        keywords = self._asset_keywords()
        if not keywords:
            PrintUtils.print_error("当前架构暂不支持自动安装 Zellij: {}".format(osarch))
            return None

        PrintUtils.print_info("正在获取 Zellij 最新 release 信息...")
        try:
            request = urllib.request.Request(ZELLIJ_RELEASE_API, headers={"User-Agent": "office-install/1.0"})
            with self._proxy_opener().open(request, timeout=60) as response:
                release = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            PrintUtils.print_error("获取 Zellij release 信息失败: {}".format(exc))
            return None

        assets = release.get("assets", [])
        for keyword in keywords:
            preferred = []
            fallback = []
            for asset in assets:
                name = asset.get("name", "")
                url = asset.get("browser_download_url", "")
                if keyword not in name or not name.endswith(".tar.gz") or not url:
                    continue
                if "no-web" in name:
                    fallback.append(asset)
                else:
                    preferred.append(asset)

            for asset in preferred + fallback:
                name = asset.get("name", "")
                url = asset.get("browser_download_url", "")
                PrintUtils.print_info("已选择 Zellij 安装包: {}".format(name))
                return url

        PrintUtils.print_error("未找到适合当前架构的 Zellij 安装包。")
        return None

    def _download_file(self, url, target_path):
        PrintUtils.print_info("下载地址: {}".format(url))
        request = urllib.request.Request(url, headers={"User-Agent": "office-install/1.0"})
        temp_path = target_path + ".part"
        downloaded = 0
        last_print = 0
        start = time.time()

        try:
            with self._proxy_opener().open(request, timeout=120) as response:
                total = int(response.headers.get("Content-Length") or 0)
                with open(temp_path, "wb") as f:
                    while True:
                        chunk = response.read(1024 * 256)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        now = time.time()
                        if now - last_print >= 0.5 or (total and downloaded >= total):
                            elapsed = max(now - start, 0.001)
                            speed = downloaded / elapsed / 1024 / 1024
                            if total:
                                percent = downloaded * 100 / total
                                sys.stdout.write("\r下载进度: {percent:6.2f}% {done:.2f}/{total:.2f} MiB {speed:.2f} MiB/s".format(
                                    percent=percent,
                                    done=downloaded / 1024 / 1024,
                                    total=total / 1024 / 1024,
                                    speed=speed,
                                ))
                            else:
                                sys.stdout.write("\r下载进度: {done:.2f} MiB {speed:.2f} MiB/s".format(
                                    done=downloaded / 1024 / 1024,
                                    speed=speed,
                                ))
                            sys.stdout.flush()
                            last_print = now
            os.replace(temp_path, target_path)
            sys.stdout.write("\n")
            return True
        except Exception as exc:
            sys.stdout.write("\n")
            try:
                os.remove(temp_path)
            except OSError:
                pass
            PrintUtils.print_error("下载失败: {}".format(exc))
            return False

    def _safe_extract(self, tar, target_dir):
        target_dir = os.path.abspath(target_dir)
        for member in tar.getmembers():
            member_path = os.path.abspath(os.path.join(target_dir, member.name))
            if not member_path.startswith(target_dir + os.sep):
                raise RuntimeError("tar archive contains unsafe path: {}".format(member.name))
        tar.extractall(target_dir)

    def _install_dependencies(self):
        packages = ["ca-certificates", "xclip", "wl-clipboard"]
        CmdTask("sudo apt update", 0).run()
        result = CmdTask("sudo apt install -y {}".format(" ".join(packages)), 0).run()
        if result[0] != 0:
            PrintUtils.print_warn("剪贴板依赖安装不完整，继续安装 Zellij。")
        return True

    def _install_binary(self, url):
        archive_path = "/tmp/zellij.tar.gz"
        extract_dir = "/tmp/zellij_extract"
        CmdTask("rm -rf {} {}".format(archive_path, extract_dir), 0).run()
        if not self._download_file(url, archive_path):
            PrintUtils.print_error("Zellij 安装包下载失败。")
            return False

        os.makedirs(extract_dir, exist_ok=True)
        try:
            with tarfile.open(archive_path, "r:gz") as tar:
                self._safe_extract(tar, extract_dir)
        except Exception as exc:
            PrintUtils.print_error("Zellij 安装包解压失败: {}".format(exc))
            return False

        zellij_path = None
        for root, _, files in os.walk(extract_dir):
            if "zellij" in files:
                zellij_path = os.path.join(root, "zellij")
                break
        if zellij_path is None:
            PrintUtils.print_error("安装包中未找到 zellij 二进制。")
            return False

        result = CmdTask("sudo install -m 0755 {} /usr/local/bin/zellij".format(shlex.quote(zellij_path)), 0).run()
        if result[0] != 0:
            PrintUtils.print_error("Zellij 二进制安装失败。")
            return False
        return True

    def _write_copy_helper(self):
        helper = """#!/bin/sh
if command -v wl-copy >/dev/null 2>&1 && [ -n \"$WAYLAND_DISPLAY\" ]; then
    exec wl-copy
fi
if command -v xclip >/dev/null 2>&1 && [ -n \"$DISPLAY\" ]; then
    exec xclip -selection clipboard
fi
cat >/tmp/zellij-copy-fallback.txt
"""
        temp_path = "/tmp/office-zellij-copy"
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(helper)
        result = CmdTask("sudo install -m 0755 {} /usr/local/bin/office-zellij-copy".format(temp_path), 0).run()
        if result[0] != 0:
            PrintUtils.print_error("Zellij 剪贴板 helper 安装失败。")
            return False
        return True

    def _write_config(self):
        user, home = self._target_user()
        config_dir = os.path.join(home, ".config", "zellij")
        config_path = os.path.join(config_dir, "config.kdl")
        os.makedirs(config_dir, exist_ok=True)

        if os.path.exists(config_path):
            backup_path = config_path + ".bak.office-install-" + time.strftime("%Y%m%d%H%M%S")
            os.replace(config_path, backup_path)
            PrintUtils.print_warn("检测到已有 Zellij 配置，已备份: {}".format(backup_path))

        config = """// Generated by office-install.
// Mouse wheel scrolls terminal history. Selecting text copies it to the system clipboard.
mouse_mode true
scroll_buffer_size 10000
copy_on_select true
copy_clipboard "system"
copy_command "office-zellij-copy"
show_startup_tips false
pane_frames false
simplified_ui true
default_layout "compact"
"""
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(config)

        if user != "root":
            CmdTask("sudo chown -R {}:{} {}".format(shlex.quote(user), shlex.quote(user), shlex.quote(config_dir)), 0).run()
        PrintUtils.print_success("Zellij 默认配置已写入: {}".format(config_path))
        return True

    def run(self):
        if not self._check_sudo():
            return False

        self._install_dependencies()
        zellij_url = self._latest_zellij_url()
        if zellij_url is None:
            return False
        if not self._install_binary(zellij_url):
            return False
        if not self._write_copy_helper():
            return False
        if not self._write_config():
            return False

        PrintUtils.print_success("Zellij 安装完成。运行 zellij 即可进入，滚轮可查看历史输出，选择文本会复制到系统剪贴板。")
        PrintUtils.print_success("已启用 simplified_ui 并关闭 pane_frames，避免缺少 Nerd Font/Powerline 字体时 Tab 栏出现乱码。")
        PrintUtils.print_success("Ctrl+Shift+C 由终端模拟器处理；若鼠标选择被 Zellij 捕获，可按住 Shift 后选择再复制。")
        return True
