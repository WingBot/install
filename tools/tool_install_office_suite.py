# -*- coding: utf-8 -*-
import glob
import hashlib
import json
import os
import re
import shlex
import shutil
import socket
import sys
import tarfile
import time
import urllib.request
from urllib.parse import urlparse

from .base import BaseTool, CmdTask, PrintUtils, ChooseTask, osarch


ZOTERO_LINUX_X64 = "https://www.zotero.org/download/client/dl?channel=release&platform=linux-x86_64"
ZOTERO_LINUX_ARM64 = "https://www.zotero.org/download/client/dl?channel=release&platform=linux-aarch64"
OBSIDIAN_RELEASE_API = "https://api.github.com/repos/obsidianmd/obsidian-releases/releases/latest"
WPS_LINUX_PAGE = "https://www.wps.cn/product/wpslinux"


class Tool(BaseTool):
    def __init__(self):
        self.name = "一键安装办公套件(Zotero/Obsidian/WPS/字体)"
        self.type = BaseTool.TYPE_INSTALL
        self.author = "WingBot"

    def _run_cmd(self, cmd, timeout=0, msg=None):
        if msg:
            PrintUtils.print_info(msg)
        return CmdTask(cmd, timeout).run()

    def _code(self, result):
        if isinstance(result, tuple) and len(result) > 0:
            return result[0]
        if isinstance(result, list) and len(result) > 0:
            return result[0]
        return -1

    def _out(self, result):
        if (
            isinstance(result, tuple)
            and len(result) > 1
            and isinstance(result[1], list)
        ):
            return result[1]
        return []

    def _local_proxy_available(self, host, port):
        try:
            with socket.create_connection((host, port), timeout=0.3):
                return True
        except OSError:
            return False

    def _proxy_opener(self, use_proxy=True):
        if not use_proxy:
            return urllib.request.build_opener(urllib.request.ProxyHandler({}))

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

    def _urlopen(self, url, timeout=60, headers=None, use_proxy=True):
        request_headers = {"User-Agent": "office-install/1.0"}
        if headers:
            request_headers.update(headers)
        request = urllib.request.Request(
            url, headers=request_headers
        )
        return self._proxy_opener(use_proxy=use_proxy).open(request, timeout=timeout)

    def _download_file(self, url, target_path, timeout=180, headers=None, use_proxy=True):
        PrintUtils.print_info("下载地址: {}".format(url))
        request_headers = {"User-Agent": "office-install/1.0"}
        if headers:
            request_headers.update(headers)
        request = urllib.request.Request(
            url, headers=request_headers
        )
        temp_path = target_path + ".part"
        downloaded = 0
        last_print = 0
        start = time.time()
        try:
            with self._proxy_opener(use_proxy=use_proxy).open(request, timeout=timeout) as response:
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
                                sys.stdout.write(
                                    "\r下载进度: {percent:6.2f}% {done:.2f}/{total:.2f} MiB {speed:.2f} MiB/s".format(
                                        percent=downloaded * 100 / total,
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

    def _check_sudo(self):
        sudo_check = self._run_cmd("sudo -n true", 0)
        if self._code(sudo_check) != 0:
            PrintUtils.print_error("当前会话无法无交互使用 sudo，请在终端中运行安装器并输入 sudo 密码后重试。")
            return False
        return True

    def _install_deb(self, deb_path, name):
        self._run_cmd("sudo apt update", 0)
        result = self._run_cmd("sudo apt install -y {}".format(shlex.quote(deb_path)), 0)
        if self._code(result) == 0:
            return True
        PrintUtils.print_warn("{} apt 安装失败，尝试修复依赖后重试。".format(name))
        self._run_cmd("sudo apt --fix-broken install -y", 0)
        result = self._run_cmd("sudo apt install -y {}".format(shlex.quote(deb_path)), 0)
        if self._code(result) != 0:
            PrintUtils.print_error("{} 安装失败，请检查网络、apt 源和系统架构。".format(name))
            return False
        return True

    def _safe_extract(self, tar, target_dir):
        target_dir = os.path.abspath(target_dir)
        for member in tar.getmembers():
            member_path = os.path.abspath(os.path.join(target_dir, member.name))
            if not member_path.startswith(target_dir + os.sep):
                raise RuntimeError("tar archive contains unsafe path: {}".format(member.name))
        tar.extractall(target_dir)

    def _target_user(self):
        return os.environ.get("SUDO_USER") or os.environ.get("LOGNAME") or os.environ.get("USER") or "root"

    def _target_home(self):
        user = self._target_user()
        if user == "root":
            return "/root"
        return os.path.expanduser("~{}".format(user))

    def _zotero_url(self):
        if osarch == "amd64":
            return ZOTERO_LINUX_X64
        if osarch == "arm64":
            return ZOTERO_LINUX_ARM64
        PrintUtils.print_error("Zotero 当前暂不支持自动安装架构: {}".format(osarch))
        return None

    def install_zotero(self):
        if not self._check_sudo():
            return False
        url = self._zotero_url()
        if url is None:
            return False

        archive_path = "/tmp/zotero.tar"
        extract_dir = "/tmp/zotero_extract"
        self._run_cmd("rm -rf {} {}".format(archive_path, extract_dir), 0)
        if not self._download_file(url, archive_path, 240):
            return False
        os.makedirs(extract_dir, exist_ok=True)

        try:
            with tarfile.open(archive_path, "r:*") as tar:
                self._safe_extract(tar, extract_dir)
        except Exception as exc:
            PrintUtils.print_error("Zotero 解压失败: {}".format(exc))
            return False

        zotero_dir = None
        for name in os.listdir(extract_dir):
            path = os.path.join(extract_dir, name)
            if os.path.isdir(path) and os.path.exists(os.path.join(path, "zotero")):
                zotero_dir = path
                break
        if zotero_dir is None:
            PrintUtils.print_error("Zotero 安装包中未找到可执行文件。")
            return False

        self._run_cmd("sudo rm -rf /opt/zotero", 0)
        if self._code(self._run_cmd("sudo mv {} /opt/zotero".format(shlex.quote(zotero_dir)), 0)) != 0:
            return False
        self._run_cmd("sudo ln -sf /opt/zotero/zotero /usr/local/bin/zotero", 0)

        if not self.repair_zotero_launcher():
            PrintUtils.print_warn("Zotero 桌面入口修复失败，请手动检查 /usr/share/applications/zotero.desktop")
        self._run_cmd("rm -rf {} {}".format(archive_path, extract_dir), 0)

        verify = self._run_cmd("zotero --version", 10, "验证 Zotero 版本...")
        if self._code(verify) != 0:
            PrintUtils.print_warn("Zotero 命令验证未通过，但桌面入口已写入。")
        PrintUtils.print_success("Zotero 安装完成。")
        return True

    def _zotero_icon_candidates(self):
        return [
            "/opt/zotero/icons/icon256.png",
            "/opt/zotero/icons/icon128.png",
            "/opt/zotero/chrome/icons/default/default256.png",
            "/opt/zotero/chrome/icons/default/default128.png",
        ]

    def repair_zotero_launcher(self):
        if not self._check_sudo():
            return False
        if not os.path.exists("/opt/zotero/zotero"):
            PrintUtils.print_error("未找到 /opt/zotero/zotero，请先安装 Zotero。")
            return False

        icon_path = None
        for candidate in self._zotero_icon_candidates():
            if os.path.exists(candidate):
                icon_path = candidate
                break
        if icon_path is None:
            PrintUtils.print_warn("未找到 Zotero 彩色图标文件，将保留 desktop 入口但图标可能由系统主题决定。")
        else:
            self._run_cmd("sudo mkdir -p /usr/share/icons/hicolor/128x128/apps", 0)
            self._run_cmd(
                "sudo install -m 0644 {} /usr/share/icons/hicolor/128x128/apps/zotero.png".format(
                    shlex.quote(icon_path)
                ),
                0,
            )

        desktop = """[Desktop Entry]
Name=Zotero
Exec=/opt/zotero/zotero --url %u
Icon=zotero
Type=Application
Terminal=false
Categories=Office;Education;
MimeType=x-scheme-handler/zotero;application/x-endnote-refer;application/x-research-info-systems;text/ris;text/x-research-info-systems;application/x-inst-for-Scientific-info;application/mods+xml;application/rdf+xml;application/x-bibtex;text/x-bibtex;application/marc;application/vnd.citationstyles.style+xml;
X-GNOME-SingleWindow=true
Comment=Zotero is a free, easy-to-use tool to help you collect, organize, cite, and share research
"""
        desktop_path = "/tmp/zotero.desktop"
        with open(desktop_path, "w", encoding="utf-8") as f:
            f.write(desktop)
        result = self._run_cmd(
            "sudo install -m 0644 {} /usr/share/applications/zotero.desktop".format(
                shlex.quote(desktop_path)
            ),
            0,
        )
        self._run_cmd("rm -f {}".format(shlex.quote(desktop_path)), 0)
        self._run_cmd("sudo gtk-update-icon-cache -f /usr/share/icons/hicolor || true", 0)
        self._run_cmd("update-desktop-database ~/.local/share/applications /usr/share/applications || true", 0)
        if self._code(result) != 0:
            PrintUtils.print_error("Zotero 桌面入口写入失败。")
            return False
        PrintUtils.print_success("Zotero 图标和桌面入口已修复。")
        return True

    def _latest_obsidian_deb_url(self):
        if osarch == "amd64":
            keyword = "amd64.deb"
        elif osarch == "arm64":
            keyword = "arm64.deb"
        else:
            PrintUtils.print_error("Obsidian 当前暂不支持自动安装架构: {}".format(osarch))
            return None

        PrintUtils.print_info("正在获取 Obsidian 最新 release 信息...")
        try:
            with self._urlopen(OBSIDIAN_RELEASE_API, 60) as response:
                release = json.loads(response.read().decode("utf-8", "ignore"))
        except Exception as exc:
            PrintUtils.print_error("获取 Obsidian release 信息失败: {}".format(exc))
            return None

        for asset in release.get("assets", []):
            name = asset.get("name", "")
            url = asset.get("browser_download_url", "")
            if name.endswith(keyword) and url:
                PrintUtils.print_info("已选择 Obsidian 安装包: {}".format(name))
                return url
        PrintUtils.print_error("未找到适合当前架构的 Obsidian deb 安装包。")
        return None

    def install_obsidian(self):
        if not self._check_sudo():
            return False
        url = self._latest_obsidian_deb_url()
        if url is None:
            return False
        deb_path = "/tmp/obsidian.deb"
        self._run_cmd("rm -f {}".format(deb_path), 0)
        if not self._download_file(url, deb_path, 240):
            return False
        ok = self._install_deb(deb_path, "Obsidian")
        self._run_cmd("rm -f {}".format(deb_path), 0)
        if ok:
            PrintUtils.print_success("Obsidian 安装完成。")
        return ok

    def _latest_wps_deb_url(self):
        if osarch != "amd64":
            PrintUtils.print_error("WPS Linux 官方 deb 当前仅支持 amd64。当前架构: {}".format(osarch))
            return None
        PrintUtils.print_info("正在读取 WPS Linux 官方下载页面...")
        try:
            with self._urlopen(WPS_LINUX_PAGE, 60) as response:
                html = response.read().decode("utf-8", "ignore")
        except Exception as exc:
            PrintUtils.print_error("读取 WPS 下载页面失败: {}".format(exc))
            return None

        urls = re.findall(r"https?://[^\"'<>\s]+\.deb(?:\?[^\"'<>\s]*)?", html)
        for url in urls:
            if "amd64" in url and "wps-office" in url:
                PrintUtils.print_info("已选择 WPS 安装包: {}".format(url.rsplit("/", 1)[-1]))
                return url

        version_match = re.search(r"(\d+\.\d+\.\d+\.\d+)", html)
        if version_match:
            version = version_match.group(1)
            build = version.rsplit(".", 1)[-1]
            fallback = "https://wps-linux-personal.wpscdn.cn/wps/download/ep/Linux2023/{build}/wps-office_{version}.AK.preread.sw.Personal_662820_amd64.deb".format(
                build=build,
                version=version,
            )
            PrintUtils.print_warn("未从页面解析到 deb 链接，尝试按版本号构造 WPS CDN 地址。")
            return fallback
        PrintUtils.print_error("未能解析 WPS deb 下载地址。")
        return None


    def _sign_wps_url(self, url):
        parsed = urlparse(url)
        timestamp = int(time.time())
        secret_key = "7f8faaaa468174dc1c9cd62e5f218a5b"
        digest = hashlib.md5(
            "{}{}{}".format(secret_key, parsed.path, timestamp).encode("utf-8")
        ).hexdigest()
        separator = "&" if "?" in url else "?"
        return "{}{}t={}&k={}".format(url, separator, timestamp, digest)

    def install_wps(self):
        if not self._check_sudo():
            return False
        url = self._latest_wps_deb_url()
        if url is None:
            return False
        deb_path = "/tmp/wps-office.deb"
        self._run_cmd("rm -f {}".format(deb_path), 0)
        url = self._sign_wps_url(url)
        wps_headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
            "Referer": WPS_LINUX_PAGE,
        }
        if not self._download_file(url, deb_path, 360, headers=wps_headers):
            PrintUtils.print_warn("WPS 通过当前代理下载失败，尝试不使用代理直接下载。")
            if not self._download_file(url, deb_path, 360, headers=wps_headers, use_proxy=False):
                return False
        ok = self._install_deb(deb_path, "WPS Office")
        self._run_cmd("rm -f {}".format(deb_path), 0)
        if ok:
            PrintUtils.print_success("WPS Office 安装完成。")
        return ok

    def install_fonts(self):
        if not self._check_sudo():
            return False
        packages = [
            "fontconfig",
            "cabextract",
            "fonts-noto-cjk",
            "fonts-noto-cjk-extra",
            "fonts-wqy-microhei",
            "fonts-wqy-zenhei",
            "fonts-arphic-ukai",
            "fonts-arphic-uming",
            "fonts-liberation",
            "fonts-liberation2",
            "fonts-crosextra-carlito",
            "fonts-crosextra-caladea",
        ]
        self._run_cmd("sudo apt update", 0)
        result = self._run_cmd("sudo apt install -y {}".format(" ".join(packages)), 0, "安装中文字体包...")
        if self._code(result) != 0:
            PrintUtils.print_warn("部分中文字体包安装失败，请检查 apt 源。")

        self._run_cmd(
            "echo 'ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true' | sudo debconf-set-selections",
            0,
        )
        ms_result = self._run_cmd(
            "sudo DEBIAN_FRONTEND=noninteractive apt install -y ttf-mscorefonts-installer",
            0,
            "安装 Microsoft core fonts...",
        )
        if self._code(ms_result) != 0:
            PrintUtils.print_warn("Microsoft core fonts 安装失败，可能是当前 apt 源未启用 multiverse/contrib。")

        self._write_office_font_aliases()
        copied = self._copy_windows_fonts()
        self._run_cmd("fc-cache -f", 0, "刷新当前用户字体缓存...")
        self._run_cmd("sudo fc-cache -f", 0, "刷新系统字体缓存...")
        if copied > 0:
            PrintUtils.print_success("已导入本机 Windows 字体 {} 个文件。".format(copied))
        PrintUtils.print_success("中文字体和 Windows 常用字体安装流程完成。")
        return True

    def _write_office_font_aliases(self):
        alias_conf = """<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">
<fontconfig>
  <alias><family>Microsoft YaHei</family><prefer><family>Noto Sans CJK SC</family><family>WenQuanYi Micro Hei</family></prefer></alias>
  <alias><family>微软雅黑</family><prefer><family>Noto Sans CJK SC</family><family>WenQuanYi Micro Hei</family></prefer></alias>
  <alias><family>DengXian</family><prefer><family>Noto Sans CJK SC</family><family>WenQuanYi Micro Hei</family></prefer></alias>
  <alias><family>等线</family><prefer><family>Noto Sans CJK SC</family><family>WenQuanYi Micro Hei</family></prefer></alias>
  <alias><family>SimSun</family><prefer><family>Noto Serif CJK SC</family><family>AR PL UMing CN</family></prefer></alias>
  <alias><family>宋体</family><prefer><family>Noto Serif CJK SC</family><family>AR PL UMing CN</family></prefer></alias>
  <alias><family>NSimSun</family><prefer><family>Noto Serif CJK SC</family><family>AR PL UMing CN</family></prefer></alias>
  <alias><family>SimHei</family><prefer><family>Noto Sans CJK SC</family><family>WenQuanYi Zen Hei</family></prefer></alias>
  <alias><family>黑体</family><prefer><family>Noto Sans CJK SC</family><family>WenQuanYi Zen Hei</family></prefer></alias>
  <alias><family>KaiTi</family><prefer><family>AR PL UKai CN</family><family>Noto Serif CJK SC</family></prefer></alias>
  <alias><family>楷体</family><prefer><family>AR PL UKai CN</family><family>Noto Serif CJK SC</family></prefer></alias>
  <alias><family>FangSong</family><prefer><family>AR PL UMing CN</family><family>Noto Serif CJK SC</family></prefer></alias>
  <alias><family>仿宋</family><prefer><family>AR PL UMing CN</family><family>Noto Serif CJK SC</family></prefer></alias>
  <alias><family>Calibri</family><prefer><family>Carlito</family><family>Liberation Sans</family></prefer></alias>
  <alias><family>Cambria</family><prefer><family>Caladea</family><family>Liberation Serif</family></prefer></alias>
  <alias><family>Arial</family><prefer><family>Liberation Sans</family><family>Arial</family></prefer></alias>
  <alias><family>Times New Roman</family><prefer><family>Liberation Serif</family><family>Times New Roman</family></prefer></alias>
  <alias><family>Courier New</family><prefer><family>Liberation Mono</family><family>Courier New</family></prefer></alias>
</fontconfig>
"""
        conf_path = "/tmp/64-office-font-aliases.conf"
        with open(conf_path, "w", encoding="utf-8") as f:
            f.write(alias_conf)
        result = self._run_cmd(
            "sudo install -m 0644 {} /etc/fonts/conf.d/64-office-font-aliases.conf".format(
                shlex.quote(conf_path)
            ),
            0,
            "写入 Office/WPS 字体替换规则...",
        )
        self._run_cmd("rm -f {}".format(shlex.quote(conf_path)), 0)
        if self._code(result) != 0:
            PrintUtils.print_warn("Office/WPS 字体替换规则写入失败。")
            return False
        return True

    def _windows_font_candidates(self):
        user = self._target_user()
        candidates = []
        env_dir = os.environ.get("WINDOWS_FONTS_DIR")
        if env_dir:
            candidates.extend([item for item in env_dir.split(":") if item.strip()])
        candidates.extend([
            "/mnt/c/Windows/Fonts",
            os.path.join(self._target_home(), "Windows", "Fonts"),
        ])
        patterns = [
            "/mnt/*/Windows/Fonts",
            "/media/{}/Windows/Fonts".format(user),
            "/media/{}/*/Windows/Fonts".format(user),
            "/run/media/{}/Windows/Fonts".format(user),
            "/run/media/{}/*/Windows/Fonts".format(user),
        ]
        for pattern in patterns:
            candidates.extend(glob.glob(pattern))

        unique = []
        seen = set()
        for path in candidates:
            normalized = os.path.abspath(os.path.expanduser(path.strip()))
            if normalized not in seen:
                seen.add(normalized)
                unique.append(normalized)
        return unique

    def _copy_windows_fonts(self):
        candidates = self._windows_font_candidates()
        home = self._target_home()
        target_dir = os.path.join(home, ".local", "share", "fonts", "windows")
        copied = 0
        used_source = None
        for source_dir in candidates:
            if not os.path.isdir(source_dir):
                continue
            font_files = [
                name for name in os.listdir(source_dir)
                if name.lower().endswith((".ttf", ".ttc", ".otf"))
            ]
            if len(font_files) == 0:
                continue
            used_source = source_dir
            os.makedirs(target_dir, exist_ok=True)
            for name in font_files:
                src = os.path.join(source_dir, name)
                dst = os.path.join(target_dir, name)
                try:
                    if not os.path.exists(dst):
                        shutil.copy2(src, dst)
                        copied += 1
                except OSError:
                    pass
            user = self._target_user()
            if user != "root":
                self._run_cmd(
                    "sudo chown -R {}:{} {}".format(
                        shlex.quote(user), shlex.quote(user), shlex.quote(target_dir)
                    ),
                    0,
                )
            break
        if used_source:
            PrintUtils.print_info("Windows 字体来源目录: {}".format(used_source))
            if copied == 0:
                PrintUtils.print_info("Windows 字体目录已存在，但没有发现需要新增复制的字体文件。")
        else:
            PrintUtils.print_warn("未发现可直接导入的 Windows 字体目录，已跳过本机 Windows 字体复制。")
            PrintUtils.print_info("请先在文件管理器中挂载 Windows 系统盘，或运行时指定: WINDOWS_FONTS_DIR=/路径/Windows/Fonts")
        return copied

    def run(self):
        choices = {
            1: "安装全部(Zotero/Obsidian/WPS/字体)",
            2: "安装 Zotero",
            3: "安装 Obsidian",
            4: "安装 WPS Office",
            5: "安装中文字体和 Windows 常用字体",
        }
        code, _ = ChooseTask(choices, "请选择要安装的办公软件:", False).run()
        if code == 1:
            ok = True
            for func in [self.install_fonts, self.install_zotero, self.install_obsidian, self.install_wps]:
                if not func():
                    ok = False
            return ok
        if code == 2:
            return self.install_zotero()
        if code == 3:
            return self.install_obsidian()
        if code == 4:
            return self.install_wps()
        if code == 5:
            return self.install_fonts()
        PrintUtils.print_warn("已取消办公软件安装")
        return False
