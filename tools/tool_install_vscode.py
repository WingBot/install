# -*- coding: utf-8 -*-
from .base import BaseTool
from .base import PrintUtils, CmdTask
from .base import osarch


class Tool(BaseTool):
    def __init__(self):
        self.name = "一键安装Vscode"
        self.type = BaseTool.TYPE_INSTALL
        self.author = "小鱼"

    def _download_url(self):
        if osarch == "amd64":
            return "https://code.visualstudio.com/sha/download?build=stable&os=linux-deb-x64"
        if osarch == "arm64":
            return "https://code.visualstudio.com/sha/download?build=stable&os=linux-deb-arm64"
        return None

    def install_vscode(self):
        url = self._download_url()
        if url is None:
            PrintUtils.print_error("当前架构暂不支持自动安装 VS Code: {}".format(osarch))
            return False

        deb_path = "/tmp/vscode.deb"
        PrintUtils.print_info("开始下载 VS Code stable 最新版: {}".format(url))
        result = CmdTask(
            "wget --show-progress --progress=bar:force:noscroll '{}' -O {} --no-check-certificate".format(url, deb_path),
            300,
        ).run()
        if result[0] != 0:
            PrintUtils.print_error("VS Code 下载失败，请检查网络。")
            return False

        PrintUtils.print_info("下载完成，开始安装 VS Code stable 最新版。")
        result = CmdTask("sudo apt install -y {}".format(deb_path), 0).run()
        if result[0] != 0:
            PrintUtils.print_warn("apt 安装失败，尝试修复依赖后重试。")
            CmdTask("sudo apt --fix-broken install -y", 0).run()
            result = CmdTask("sudo apt install -y {}".format(deb_path), 0).run()
            if result[0] != 0:
                CmdTask("rm -f {}".format(deb_path), 0).run()
                PrintUtils.print_error("VS Code 安装失败。")
                return False

        CmdTask("rm -f {}".format(deb_path), 0).run()
        PrintUtils.print_success("VS Code stable 最新版安装完成。")
        return True

    def run(self):
        return self.install_vscode()
