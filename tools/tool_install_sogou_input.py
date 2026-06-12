# -*- coding: utf-8 -*-
import json
import os
import pwd
import re
import shlex
import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.request

from .base import BaseTool, CmdTask, PrintUtils, osarch


SOGOU_LINUX_PAGE = "https://shurufa.sogou.com/linux"
FALLBACK_DOWNLOADS = {
    "amd64": "https://ime.gtimg.com/pc/dl/gzindex/1680521603/sogoupinyin_4.2.1.145_amd64.deb",
    "arm64": "https://ime.gtimg.com/pc/dl/gzindex/1680521473/sogoupinyin_4.2.1.145_arm64.deb",
}


class Tool(BaseTool):
    def __init__(self):
        self.name = "搜狗输入法"
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
            with socket.create_connection((host, port), timeout=0.3):
                return True
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

    def _arch_name(self):
        if osarch == "amd64":
            return "x86_64", "amd64"
        if osarch == "arm64":
            return "arm64", "arm64"
        return None, None

    def _normalize_download_url(self, url):
        if "://ime-sec.gtimg.com/" in url:
            return url.replace("://ime-sec.gtimg.com/", "://ime.gtimg.com/")
        return url

    def _latest_deb_url(self):
        display_arch, deb_arch = self._arch_name()
        if deb_arch is None:
            PrintUtils.print_error("当前架构暂不支持自动安装搜狗输入法: {}".format(osarch))
            return None

        try:
            PrintUtils.print_info("正在读取搜狗输入法 Linux 官方下载页面...")
            request = urllib.request.Request(SOGOU_LINUX_PAGE, headers={"User-Agent": "Mozilla/5.0"})
            with self._proxy_opener().open(request, timeout=60) as response:
                page = response.read().decode("utf-8", errors="ignore")
            match = re.search(r'"downloadConfig":"(.*?)","downloadStatus"', page)
            if match:
                config_text = bytes(match.group(1), "utf-8").decode("unicode_escape")
                config = json.loads(config_text)
                for item in config.get("linux", []):
                    name = item.get("name", "")
                    link = item.get("link", "")
                    if link and (name == display_arch or link.endswith("_{}.deb".format(deb_arch))):
                        link = self._normalize_download_url(link)
                        PrintUtils.print_info("已选择搜狗输入法安装包: {}".format(link.rsplit("/", 1)[-1]))
                        return link
        except Exception as exc:
            PrintUtils.print_warn("解析搜狗官方下载页面失败，使用内置备用地址: {}".format(exc))

        fallback = FALLBACK_DOWNLOADS.get(deb_arch)
        if fallback:
            PrintUtils.print_warn("使用搜狗输入法备用下载地址: {}".format(fallback))
        return fallback

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

    def _install_dependencies(self):
        packages = [
            "fcitx",
            "fcitx-bin",
            "fcitx-config-gtk",
            "fcitx-tools",
            "fcitx-ui-classic",
            "fcitx-module-dbus",
            "fcitx-module-kimpanel",
            "fcitx-frontend-gtk2",
            "fcitx-frontend-gtk3",
            "fcitx-frontend-qt5",
            "im-config",
            "libqt5qml5",
            "libqt5quick5",
            "libqt5quickwidgets5",
            "libgsettings-qt1",
            "qml-module-gsettings1.0",
            "qml-module-qtquick2",
        ]
        CmdTask("sudo apt update", 0).run()
        result = CmdTask("sudo apt install -y {}".format(" ".join(packages)), 0).run()
        if result[0] != 0:
            PrintUtils.print_warn("部分 fcitx/Qt 依赖安装失败，继续尝试安装搜狗输入法 deb 并自动修复依赖。")
        return True

    def _install_deb(self, deb_path):
        result = CmdTask("sudo apt install -y {}".format(deb_path), 0).run()
        if result[0] == 0:
            return True
        PrintUtils.print_warn("apt 安装搜狗输入法失败，尝试修复依赖后重试。")
        CmdTask("sudo apt --fix-broken install -y", 0).run()
        result = CmdTask("sudo apt install -y {}".format(deb_path), 0).run()
        if result[0] != 0:
            PrintUtils.print_error("搜狗输入法安装失败，请检查系统版本、apt 源和桌面环境。")
            return False
        return True

    def _configure_fcitx(self):
        user, home = self._target_user()
        env_block = """# >>> office install fcitx >>>
export GTK_IM_MODULE=fcitx
export QT_IM_MODULE=fcitx
export XMODIFIERS=@im=fcitx
# <<< office install fcitx <<<
"""
        for file_name in [".xprofile", ".profile"]:
            path = os.path.join(home, file_name)
            try:
                data = ""
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        data = f.read()
                start = data.find("# >>> office install fcitx >>>")
                end = data.find("# <<< office install fcitx <<<")
                if start >= 0 and end >= start:
                    data = data[:start] + data[end + len("# <<< office install fcitx <<<"):].lstrip("\n")
                if data and not data.endswith("\n"):
                    data += "\n"
                data += env_block
                with open(path, "w", encoding="utf-8") as f:
                    f.write(data)
                if user != "root":
                    CmdTask("sudo chown {}:{} {}".format(shlex.quote(user), shlex.quote(user), shlex.quote(path)), 0).run()
            except Exception as exc:
                PrintUtils.print_warn("写入 {} 失败: {}".format(path, exc))

        xinputrc_path = os.path.join(home, ".xinputrc")
        try:
            if os.path.exists(xinputrc_path):
                with open(xinputrc_path, "r", encoding="utf-8", errors="ignore") as f:
                    old_xinputrc = f.read().strip()
                if old_xinputrc and old_xinputrc != "run_im fcitx":
                    backup_path = xinputrc_path + ".bak.office-install-" + time.strftime("%Y%m%d%H%M%S")
                    os.replace(xinputrc_path, backup_path)
                    PrintUtils.print_warn("检测到已有 .xinputrc，已备份: {}".format(backup_path))
            with open(xinputrc_path, "w", encoding="utf-8") as f:
                f.write("run_im fcitx\n")
            if user != "root":
                CmdTask("sudo chown {}:{} {}".format(shlex.quote(user), shlex.quote(user), shlex.quote(xinputrc_path)), 0).run()
        except Exception as exc:
            PrintUtils.print_warn("写入 {} 失败: {}".format(xinputrc_path, exc))

        autostart_dir = os.path.join(home, ".config", "autostart")
        autostart_path = os.path.join(autostart_dir, "fcitx.desktop")
        try:
            os.makedirs(autostart_dir, exist_ok=True)
            desktop = """[Desktop Entry]
Type=Application
Name=Fcitx
Exec=fcitx -r -d
Terminal=false
X-GNOME-Autostart-enabled=true
"""
            with open(autostart_path, "w", encoding="utf-8") as f:
                f.write(desktop)
            if user != "root":
                CmdTask("sudo chown -R {}:{} {}".format(shlex.quote(user), shlex.quote(user), shlex.quote(autostart_dir)), 0).run()
        except Exception as exc:
            PrintUtils.print_warn("写入 {} 失败: {}".format(autostart_path, exc))

        CmdTask("sudo -u {} im-config -n fcitx".format(shlex.quote(user)) if user != "root" else "im-config -n fcitx", 0).run()
        self._prefer_sogou_input_method(user, home)
        self._start_fcitx_nonblocking(user, home)
        PrintUtils.print_success("已配置当前用户使用 fcitx，并写入 .xinputrc 与桌面自启动。请注销并重新登录后启用搜狗输入法。")
        return True

    def _prefer_sogou_input_method(self, user, home):
        fcitx_dir = os.path.join(home, ".config", "fcitx")
        profile_path = os.path.join(fcitx_dir, "profile")
        config_path = os.path.join(fcitx_dir, "config")
        try:
            os.makedirs(fcitx_dir, exist_ok=True)
            profile = ""
            if os.path.exists(profile_path):
                with open(profile_path, "r", encoding="utf-8", errors="ignore") as f:
                    profile = f.read()

            if "[Profile]" not in profile:
                profile = "[Profile]\n" + profile
            lines = profile.splitlines()
            has_im_name = False
            has_enabled_list = False
            for index, line in enumerate(lines):
                if line.startswith("IMName="):
                    lines[index] = "IMName=sogoupinyin"
                    has_im_name = True
                elif line.startswith("EnabledIMList="):
                    value = line.split("=", 1)[1]
                    items = [item for item in value.split(",") if item]
                    lines[index] = "EnabledIMList=sogoupinyin:True,fcitx-keyboard-us:False"
                    has_enabled_list = True
            if not has_im_name:
                lines.append("IMName=sogoupinyin")
            if not has_enabled_list:
                lines.append("EnabledIMList=sogoupinyin:True,fcitx-keyboard-us:False")
            with open(profile_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")

            config = ""
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8", errors="ignore") as f:
                    config = f.read()
            if "DefaultInputMethodState=" in config:
                config = re.sub(r"(?m)^#?DefaultInputMethodState=.*$", "DefaultInputMethodState=Active", config)
            else:
                if "[Program]" not in config:
                    config += "\n[Program]\n"
                config += "DefaultInputMethodState=Active\n"
            with open(config_path, "w", encoding="utf-8") as f:
                f.write(config)

            if user != "root":
                CmdTask("sudo chown -R {}:{} {}".format(shlex.quote(user), shlex.quote(user), shlex.quote(fcitx_dir)), 0).run()
            PrintUtils.print_success("已将 fcitx 当前输入法设置为 sogoupinyin。")
        except Exception as exc:
            PrintUtils.print_warn("设置 fcitx 当前输入法为 sogoupinyin 失败: {}".format(exc))
        return True

    def _start_fcitx_nonblocking(self, user, home):
        sogou_config_dir = os.path.join(home, ".config", "sogoupinyin")
        try:
            os.makedirs(sogou_config_dir, exist_ok=True)
            logf_path = os.path.join(sogou_config_dir, "logf.conf")
            if not os.path.exists(logf_path):
                source_log_conf = "/opt/sogoupinyin/files/share/conf/log/log.conf"
                if os.path.exists(source_log_conf):
                    with open(source_log_conf, "r", encoding="utf-8", errors="ignore") as src:
                        logf_data = src.read()
                else:
                    logf_data = "log4cplus.logger.sogou=ERROR\n"
                with open(logf_path, "w", encoding="utf-8") as dst:
                    dst.write(logf_data)
            if user != "root":
                CmdTask("sudo chown -R {}:{} {}".format(shlex.quote(user), shlex.quote(user), shlex.quote(sogou_config_dir)), 0).run()
        except Exception as exc:
            PrintUtils.print_warn("准备搜狗输入法配置目录失败: {}".format(exc))

        command = ["fcitx", "-r", "-d"]
        if user != "root":
            command = ["sudo", "-u", user, "env", "HOME={}".format(home)] + command
        try:
            subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )
            PrintUtils.print_success("已尝试后台重启 fcitx。")
        except Exception as exc:
            PrintUtils.print_warn("后台重启 fcitx 失败，可注销重登后生效: {}".format(exc))
        return True

    def run(self):
        if not self._check_sudo():
            return False

        deb_url = self._latest_deb_url()
        if deb_url is None:
            return False

        deb_path = "/tmp/sogoupinyin.deb"
        CmdTask("rm -f {}".format(deb_path), 0).run()
        if not self._download_file(deb_url, deb_path):
            return False

        self._install_dependencies()
        if not self._install_deb(deb_path):
            return False

        CmdTask("rm -f {}".format(deb_path), 0).run()
        self._configure_fcitx()
        PrintUtils.print_success("搜狗输入法安装完成。若未立即出现，请注销/重启后在 fcitx 配置中添加搜狗拼音。")
        return True
