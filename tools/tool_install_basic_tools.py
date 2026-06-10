# -*- coding: utf-8 -*-
from .base import BaseTool, CmdTask, PrintUtils


class Tool(BaseTool):
    def __init__(self):
        self.name = "基础工具包"
        self.type = BaseTool.TYPE_INSTALL
        self.author = "WingBot"

    def run(self):
        packages = [
            "ca-certificates",
            "curl",
            "wget",
            "git",
            "unzip",
            "xz-utils",
        ]
        PrintUtils.print_info("开始安装基础工具包: {}".format(", ".join(packages)))

        apt_check = CmdTask("command -v apt-get", 0).run()
        if apt_check[0] != 0:
            PrintUtils.print_error("当前系统未检测到 apt-get，暂只支持 Ubuntu/Debian 系统。")
            return False

        sudo_check = CmdTask("sudo -n true", 0).run()
        if sudo_check[0] != 0:
            PrintUtils.print_error("当前会话无法无交互使用 sudo，请在终端中运行安装器并输入 sudo 密码后重试。")
            return False

        CmdTask("sudo apt update", 0).run()
        result = CmdTask("sudo apt install -y {}".format(" ".join(packages)), 0).run()
        if result[0] != 0:
            PrintUtils.print_error("基础工具包安装失败，请检查 apt 源和网络连接。")
            return False

        PrintUtils.print_success("基础工具包安装完成。")
        return True
