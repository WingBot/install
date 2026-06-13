# -*- coding: utf-8 -*-
import json
import os
import sys
import time
import shlex
import socket
import urllib.request

from .base import BaseTool, CmdTask, PrintUtils, ChooseTask, osarch


RUSTDESK_CONFIG = "=0nI9AjRvNXTkllVqdmaRdzbHB1QndWYNhnUFl0ZoxWeDFzNItiTWFEb2RlYZtiI6ISeltmIsIiI6ISawFmIsIiI6ISehxWZyJCLiYTMxEjM6YTMuUDNuUTNx4COiojI0N3boJye"
RELEASE_API = "https://api.github.com/repos/rustdesk/rustdesk/releases/latest"


class Tool(BaseTool):
    def __init__(self):
        self.name = "RustDesk远程控制"
        self.type = BaseTool.TYPE_INSTALL
        self.author = "WingBot"
        self.mode = "install"

    def set_mode(self, mode):
        self.mode = mode
        if mode == "uninstall":
            self.type = BaseTool.TYPE_UNINSTALL

    def _asset_arch_keyword(self):
        if osarch == "amd64":
            return "x86_64"
        if osarch == "arm64":
            return "aarch64"
        return None

    def _latest_deb_url(self):
        arch_keyword = self._asset_arch_keyword()
        if arch_keyword is None:
            PrintUtils.print_error("当前架构暂不支持自动安装 RustDesk: {}".format(osarch))
            return None

        PrintUtils.print_info("正在获取 RustDesk 最新 release 信息...")
        try:
            with self._proxy_opener().open(RELEASE_API, timeout=60) as response:
                release = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            PrintUtils.print_error("获取 RustDesk release 信息失败: {}".format(exc))
            return None

        deb_assets = self._candidate_deb_assets(release, arch_keyword)
        if not deb_assets:
            PrintUtils.print_error("未找到适合当前架构的 RustDesk deb 安装包。")
            return None

        for asset in deb_assets:
            name = asset.get("name", "")
            if "sciter" not in name.lower():
                PrintUtils.print_info("已选择 RustDesk 主线 deb 包: {}".format(name))
                return asset.get("browser_download_url")

        fallback = deb_assets[0]
        PrintUtils.print_warn(
            "未找到非 sciter 主线 deb 包，回退使用: {}".format(fallback.get("name", ""))
        )
        return fallback.get("browser_download_url")

    def _candidate_deb_assets(self, release, arch_keyword):
        deb_assets = []
        for asset in release.get("assets", []):
            name = asset.get("name", "")
            url = asset.get("browser_download_url", "")
            if name.endswith(".deb") and arch_keyword in name and url:
                deb_assets.append(asset)
        return deb_assets

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
            with socket.create_connection((host, port), timeout=0.3):
                return True
        except OSError:
            return False

    def _check_sudo(self):
        sudo_check = CmdTask("sudo -n true", 0).run()
        if sudo_check[0] != 0:
            PrintUtils.print_error("当前会话无法无交互使用 sudo，请在终端中运行安装器并输入 sudo 密码后重试。")
            return False
        return True

    def _choose_action(self):
        actions = {
            1: "安装或重装 RustDesk，并导入配置和固定密码",
            2: "仅修复 RustDesk 配置、固定密码和开机自启",
            3: "卸载 RustDesk 并清理当前用户配置",
        }
        code, _ = ChooseTask(actions, "请选择 RustDesk 操作:", False).run()
        return code

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

    def _install_package(self, deb_url):
        deb_path = "/tmp/rustdesk.deb"
        CmdTask("rm -f {}".format(deb_path), 0).run()
        if not self._download_file(deb_url, deb_path):
            PrintUtils.print_error("RustDesk 安装包下载失败。")
            return False

        install_result = CmdTask("sudo apt install -y {}".format(deb_path), 0).run()
        if install_result[0] != 0:
            PrintUtils.print_warn("apt 直接安装失败，尝试修复依赖后重新安装。")
            CmdTask("sudo apt --fix-broken install -y", 0).run()
            install_result = CmdTask("sudo apt install -y {}".format(deb_path), 0).run()
            if install_result[0] != 0:
                PrintUtils.print_error("RustDesk 安装失败，请检查 apt 源和网络连接。")
                return False

        CmdTask("rm -f {}".format(deb_path), 0).run()
        return True

    def _import_config(self):
        rustdesk_bin = CmdTask("command -v rustdesk", 0).run()
        if rustdesk_bin[0] != 0:
            PrintUtils.print_error("未找到 rustdesk 命令，无法导入服务器配置。")
            return False

        import_result = CmdTask(
            "sudo rustdesk --config {}".format(shlex.quote(RUSTDESK_CONFIG)), 0
        ).run()
        if import_result[0] != 0:
            PrintUtils.print_error("RustDesk 服务器配置导入失败，请打开 RustDesk 后手动导入配置。")
            return False

        PrintUtils.print_success("RustDesk 已导入 ID/中继服务器配置。")
        return True

    def _target_username(self):
        username = os.environ.get("SUDO_USER") or os.environ.get("LOGNAME") or os.environ.get("USER") or "user"
        if username == "root":
            username = "user"
        return username[:1].upper() + username[1:]

    def _fixed_password(self):
        return "{}#2026".format(self._target_username())

    def _set_permanent_password(self):
        password = self._fixed_password()
        result = CmdTask(
            "sudo rustdesk --password {}".format(shlex.quote(password)), 0
        ).run()
        if result[0] != 0:
            PrintUtils.print_error("RustDesk 固定密码设置失败，请确认 RustDesk 已安装并正在运行服务。")
            return False

        PrintUtils.print_success("RustDesk 固定密码已设置为: {}".format(password))
        return True

    def _enable_autostart(self):
        result = CmdTask("sudo systemctl enable --now rustdesk", 0).run()
        if result[0] == 0:
            PrintUtils.print_success("RustDesk systemd 服务已设置为开机自启。")
            return True

        PrintUtils.print_warn("未能启用 rustdesk systemd 服务，可能当前安装包未提供该服务。")
        return False

    def _uninstall(self):
        if not self._check_sudo():
            return False

        PrintUtils.print_info("开始卸载 RustDesk，并清理当前用户配置。")
        CmdTask("sudo apt remove -y rustdesk", 0).run()
        CmdTask("sudo apt purge -y rustdesk", 0).run()
        CmdTask("sudo apt autoremove -y", 0).run()
        CmdTask("rm -rf ~/.config/rustdesk ~/.local/share/rustdesk", 0).run()
        PrintUtils.print_success("RustDesk 已卸载，当前用户配置已清理。")
        return True

    def _install(self):
        if not self._check_sudo():
            return False

        deb_url = self._latest_deb_url()
        if deb_url is None:
            return False

        PrintUtils.print_info("RustDesk deb 下载地址: {}".format(deb_url))
        if not self._install_package(deb_url):
            return False

        self._enable_autostart()
        if not self._import_config():
            return False
        return self._set_permanent_password()

    def _repair_config(self):
        if not self._check_sudo():
            return False

        rustdesk_bin = CmdTask("command -v rustdesk", 0).run()
        if rustdesk_bin[0] != 0:
            PrintUtils.print_error("未检测到 RustDesk，请先选择安装或重装。")
            return False

        self._enable_autostart()
        if not self._import_config():
            return False
        return self._set_permanent_password()

    def run(self):
        if self.mode == "uninstall":
            return self._uninstall()
        if self.mode == "repair":
            return self._repair_config()

        action = self._choose_action()
        if action == 1:
            return self._install()
        if action == 2:
            return self._repair_config()
        if action == 3:
            return self._uninstall()

        PrintUtils.print_warn("已取消 RustDesk 操作")
        return False
