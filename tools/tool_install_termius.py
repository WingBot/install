# -*- coding: utf-8 -*-
import os
import socket
import subprocess
import sys
import time
import urllib.request
from urllib.parse import urlparse

from .base import BaseTool
from .base import PrintUtils, CmdTask
from .base import osarch


class Tool(BaseTool):
    def __init__(self):
        self.name = "Termius SSH 客户端"
        self.type = BaseTool.TYPE_INSTALL
        self.author = "WingBot"

    def _download_url(self):
        if osarch == "amd64":
            return "https://www.termius.com/download/linux/Termius.deb"
        PrintUtils.print_error("Termius 官方 deb 当前仅提供 amd64 版本，当前架构: {}".format(osarch))
        return None

    def _system_proxy_candidates(self):
        candidates = []
        explicit_proxy = os.environ.get("OFFICE_INSTALL_PROXY")
        if explicit_proxy:
            candidates.append(explicit_proxy)

        try:
            mode = subprocess.run(
                ["gsettings", "get", "org.gnome.system.proxy", "mode"],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=1,
            ).stdout.strip().strip("'")
            if mode == "manual":
                for schema in ["http", "https"]:
                    host = subprocess.run(
                        ["gsettings", "get", "org.gnome.system.proxy.{}".format(schema), "host"],
                        check=False,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.DEVNULL,
                        text=True,
                        timeout=1,
                    ).stdout.strip().strip("'")
                    port_text = subprocess.run(
                        ["gsettings", "get", "org.gnome.system.proxy.{}".format(schema), "port"],
                        check=False,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.DEVNULL,
                        text=True,
                        timeout=1,
                    ).stdout.strip()
                    if host and port_text.isdigit() and int(port_text) > 0:
                        candidates.append("http://{}:{}".format(host, port_text))
        except (OSError, subprocess.SubprocessError):
            pass

        for port in [7897, 7890, 7891, 7892]:
            candidates.append("http://127.0.0.1:{}".format(port))

        deduped = []
        seen = set()
        for candidate in candidates:
            if candidate not in seen:
                seen.add(candidate)
                deduped.append(candidate)
        return deduped

    def _detect_local_proxy_url(self):
        for proxy_url in self._system_proxy_candidates():
            parsed = urlparse(proxy_url)
            host = parsed.hostname
            port = parsed.port
            if parsed.scheme not in ["http", "https"] or not host or not port:
                continue
            if self._local_proxy_available(host, port):
                return proxy_url
        return None

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

        if not proxies:
            proxy_url = self._detect_local_proxy_url()
            if proxy_url:
                proxies = {"http": proxy_url, "https": proxy_url}
                PrintUtils.print_info("检测到本地代理，下载将使用: {}".format(proxy_url))

        if proxies:
            return urllib.request.build_opener(urllib.request.ProxyHandler(proxies))
        return urllib.request.build_opener()

    def _download_file(self, url, target_path):
        PrintUtils.print_info("下载地址: {}".format(url))
        request = urllib.request.Request(url, headers={"User-Agent": "office-install/1.0"})
        temp_path = target_path + ".part"
        downloaded = 0
        last_print = 0
        start = time.time()

        try:
            with self._proxy_opener().open(request, timeout=180) as response:
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
                                sys.stdout.write(
                                    "\r下载进度: {percent:6.2f}% {done:.2f}/{total:.2f} MiB {speed:.2f} MiB/s".format(
                                        percent=percent,
                                        done=downloaded / 1024 / 1024,
                                        total=total / 1024 / 1024,
                                        speed=speed,
                                    )
                                )
                            else:
                                sys.stdout.write(
                                    "\r下载进度: {done:.2f} MiB {speed:.2f} MiB/s".format(
                                        done=downloaded / 1024 / 1024,
                                        speed=speed,
                                    )
                                )
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

    def _run_visible(self, command):
        PrintUtils.print_info("执行命令: {}".format(command))
        return subprocess.call(command, shell=True)

    def install_termius(self):
        url = self._download_url()
        if url is None:
            PrintUtils.print_error("当前架构暂不支持自动安装 Termius: {}".format(osarch))
            return False

        deb_path = "/tmp/termius.deb"
        CmdTask("rm -f {} {}.part".format(deb_path, deb_path), 0).run()
        PrintUtils.print_info("开始下载 Termius。")
        if not self._download_file(url, deb_path):
            PrintUtils.print_error("Termius 下载失败，请检查网络。")
            return False

        PrintUtils.print_info("下载完成，开始安装 Termius。")
        code = self._run_visible("sudo DEBIAN_FRONTEND=noninteractive apt install -y {}".format(deb_path))
        if code != 0:
            PrintUtils.print_warn("apt 安装失败，尝试修复依赖后重试。")
            self._run_visible("sudo DEBIAN_FRONTEND=noninteractive apt --fix-broken install -y")
            code = self._run_visible("sudo DEBIAN_FRONTEND=noninteractive apt install -y {}".format(deb_path))
            if code != 0:
                CmdTask("rm -f {}".format(deb_path), 0).run()
                PrintUtils.print_error("Termius 安装失败。")
                return False

        CmdTask("rm -f {}".format(deb_path), 0).run()
        PrintUtils.print_success("Termius安装完成。")
        return True

    def run(self):
        return self.install_termius()
