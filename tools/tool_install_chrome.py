# -*- coding: utf-8 -*-
import os
import socket
import sys
import time
import urllib.request

from .base import BaseTool, CmdTask, PrintUtils, osarch


CHROME_DEB_URL = "https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb"


class Tool(BaseTool):
    def __init__(self):
        self.name = "Google Chrome"
        self.type = BaseTool.TYPE_INSTALL
        self.author = "WingBot"

    def _check_sudo(self):
        sudo_check = CmdTask("sudo -n true", 0).run()
        if sudo_check[0] != 0:
            PrintUtils.print_error("当前会话无法无交互使用 sudo，请在终端中运行安装器并输入 sudo 密码后重试。")
            return False
        return True

    def _local_proxy_available(self, host, port):
        try:
            with socket.create_connection((host, port), timeout=0.3):
                return True
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

        if not proxies and self._local_proxy_available("127.0.0.1", 7897):
            proxy_url = "http://127.0.0.1:7897"
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

    def _install_deb(self, deb_path):
        CmdTask("sudo apt update", 0).run()
        result = CmdTask("sudo apt install -y {}".format(deb_path), 0).run()
        if result[0] == 0:
            return True

        PrintUtils.print_warn("apt 安装 Chrome 失败，尝试修复依赖后重试。")
        CmdTask("sudo apt --fix-broken install -y", 0).run()
        result = CmdTask("sudo apt install -y {}".format(deb_path), 0).run()
        if result[0] != 0:
            PrintUtils.print_error("Google Chrome 安装失败，请检查网络、apt 源和系统架构。")
            return False
        return True

    def run(self):
        if osarch != "amd64":
            PrintUtils.print_error("Google Chrome Linux 官方 deb 当前仅支持 amd64。当前架构: {}".format(osarch))
            PrintUtils.print_warn("arm64 等架构可考虑安装 Chromium 或使用其它浏览器方案。")
            return False

        if not self._check_sudo():
            return False

        deb_path = "/tmp/google-chrome-stable.deb"
        CmdTask("rm -f {}".format(deb_path), 0).run()
        if not self._download_file(CHROME_DEB_URL, deb_path):
            return False

        if not self._install_deb(deb_path):
            return False

        CmdTask("rm -f {}".format(deb_path), 0).run()
        PrintUtils.print_success("Google Chrome 安装完成。可运行 google-chrome 或在应用菜单中启动。")
        return True
