# -*- coding: utf-8 -*-
from .base import BaseTool, CmdTask, PrintUtils


class Tool(BaseTool):
    def __init__(self):
        self.name = "桌面截图和录屏工具"
        self.type = BaseTool.TYPE_INSTALL
        self.author = "WingBot"

    def _check_sudo(self):
        sudo_check = CmdTask("sudo -n true", 0).run()
        if sudo_check[0] != 0:
            PrintUtils.print_error("当前会话无法无交互使用 sudo，请在终端中运行安装器并输入 sudo 密码后重试。")
            return False
        return True

    def _package_available(self, package):
        result = CmdTask("apt-cache show {} >/dev/null 2>&1".format(package), 0).run()
        return result[0] == 0

    def _install_packages(self, packages, required=False):
        available = []
        missing = []
        for package in packages:
            if self._package_available(package):
                available.append(package)
            else:
                missing.append(package)

        if missing:
            PrintUtils.print_warn("当前 apt 源未找到以下软件包，已跳过: {}".format(", ".join(missing)))

        if not available:
            if required:
                PrintUtils.print_error("没有找到可安装的软件包: {}".format(", ".join(packages)))
                return False
            return True

        PrintUtils.print_info("准备安装: {}".format(", ".join(available)))
        result = CmdTask("sudo DEBIAN_FRONTEND=noninteractive apt install -y {}".format(" ".join(available)), 0).run()
        if result[0] != 0:
            if required:
                PrintUtils.print_error("必需软件包安装失败: {}".format(", ".join(available)))
                return False
            PrintUtils.print_warn("部分软件包安装失败: {}".format(", ".join(available)))
        return True

    def run(self):
        if not self._check_sudo():
            return False

        apt_check = CmdTask("command -v apt-get", 0).run()
        if apt_check[0] != 0:
            PrintUtils.print_error("当前系统未检测到 apt-get，暂只支持 Ubuntu/Debian 系统。")
            return False

        CmdTask("sudo apt update", 0).run()

        required_packages = [
            "flameshot",
            "ffmpeg",
        ]
        optional_packages = [
            "peek",
            "gnome-screenshot",
            "simplescreenrecorder",
            "xclip",
            "xsel",
            "wl-clipboard",
            "imagemagick",
        ]

        if not self._install_packages(required_packages, required=True):
            return False
        self._install_packages(optional_packages, required=False)

        PrintUtils.print_success("桌面截图和录屏工具安装完成。")
        PrintUtils.print_delay("Flameshot 截图: flameshot gui")
        PrintUtils.print_delay("Peek GIF 录屏: peek")
        PrintUtils.print_delay("若 Wayland 下 Flameshot 无法截屏，请尝试切换到 X11 会话或使用系统截图工具。")
        return True
