# -*- coding: utf-8 -*-
from .base import BaseTool
from .base import PrintUtils, CmdTask, ChooseTask
from .tool_install_nodejs import Tool as NodejsTool


class Tool(BaseTool):
    NPM_MIRROR = "https://registry.npmmirror.com"

    AGENTS = {
        "codex": {
            "name": "OpenAI Codex CLI",
            "package": "@openai/codex",
            "command": "codex",
            "min_node": 18,
            "login_hint": "运行 codex 后按提示登录 ChatGPT 或配置 API Key。",
        },
        "claude": {
            "name": "Claude Code",
            "package": "@anthropic-ai/claude-code",
            "command": "claude",
            "min_node": 18,
            "login_hint": "运行 claude 后按提示登录 Anthropic/Claude 账号。",
        },
        "copilot": {
            "name": "GitHub Copilot CLI",
            "package": "@github/copilot",
            "command": "copilot",
            "min_node": 22,
            "login_hint": "运行 copilot 后使用 /login 登录 GitHub；需要可用的 Copilot 订阅或组织授权。",
        },
    }

    def __init__(self):
        self.name = "一键安装AI编程助手(Codex/Claude Code/Copilot)"
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

    def _err(self, result):
        if (
            isinstance(result, tuple)
            and len(result) > 2
            and isinstance(result[2], list)
        ):
            return result[2]
        return []

    def _has_text(self, result, keyword):
        keyword = str(keyword).lower()
        for line in self._out(result) + self._err(result):
            if keyword in str(line).lower():
                return True
        return False

    def _node_major(self):
        result = self._run_cmd("node -v", 10)
        if self._code(result) != 0 or len(self._out(result)) == 0:
            return None
        version = str(self._out(result)[0]).strip().lstrip("v")
        major = version.split(".")[0]
        return int(major) if major.isdigit() else None

    def _ensure_nodejs(self, min_major):
        current_major = self._node_major()
        if current_major is not None and current_major >= min_major:
            self._run_cmd("node -v", 10, "当前 Node.js 版本:")
            self._run_cmd("npm -v", 10, "当前 npm 版本:")
            return True

        PrintUtils.print_warn(
            "当前 Node.js 不存在或版本低于 {}，将安装/升级到当前最新 LTS。".format(
                min_major
            )
        )
        return NodejsTool().install_nodejs_version(None, with_registry=False)

    def _fix_npm_prefix(self):
        prefix_result = self._run_cmd("sudo npm prefix -g", 10, "检查 npm 全局目录...")
        if self._code(prefix_result) != 0 or len(self._out(prefix_result)) == 0:
            PrintUtils.print_warn("未能读取 sudo 环境 npm 全局目录")
            return False

        prefix = str(self._out(prefix_result)[0]).strip()
        if not prefix.startswith("/root"):
            return True

        PrintUtils.print_warn("检测到 npm 全局目录位于 /root，开始修复为 /usr/local")
        self._run_cmd("sudo npm config delete prefix", 10)
        result = self._run_cmd("sudo npm config set prefix /usr/local", 10)
        return self._code(result) == 0

    def _npm_install_cmds(self, package_name):
        return [
            (
                "sudo npm install -g {} --registry={}".format(
                    package_name, self.NPM_MIRROR
                ),
                "使用 npmmirror 安装 {} ...".format(package_name),
            ),
            (
                "sudo npm install -g {}".format(package_name),
                "镜像源安装失败，回退官方 npm 源安装 {} ...".format(package_name),
            ),
        ]

    def _link_command(self, command_name):
        command_check = self._run_cmd("command -v {}".format(command_name), 10)
        if self._code(command_check) == 0:
            return True

        prefix_result = self._run_cmd("sudo npm prefix -g", 10)
        if self._code(prefix_result) != 0 or len(self._out(prefix_result)) == 0:
            return False

        npm_prefix = str(self._out(prefix_result)[0]).strip()
        if npm_prefix.startswith("/root"):
            return False
        result = self._run_cmd(
            "sudo ln -sf {}/bin/{} /usr/local/bin/{}".format(
                npm_prefix, command_name, command_name
            ),
            10,
            "写入 {} 命令到系统 PATH...".format(command_name),
        )
        return self._code(result) == 0

    def _install_agent(self, key):
        agent = self.AGENTS[key]
        PrintUtils.print_info("准备安装 {}".format(agent["name"]))

        if not self._ensure_nodejs(agent["min_node"]):
            PrintUtils.print_error("Node.js 环境准备失败，无法安装 {}".format(agent["name"]))
            return False

        if not self._fix_npm_prefix():
            PrintUtils.print_warn("npm 全局目录修复失败，安装可能受影响")

        self._run_cmd("npm config get registry", 10, "当前 npm 源:")
        installed = False
        for cmd, msg in self._npm_install_cmds(agent["package"]):
            result = self._run_cmd(cmd, 360, msg)
            if self._code(result) == 0:
                installed = True
                break
            if self._has_text(result, "ignore-scripts"):
                PrintUtils.print_warn("检测到 npm ignore-scripts 可能阻止二进制安装")

        if not installed:
            PrintUtils.print_error("{} 安装失败".format(agent["name"]))
            return False

        if not self._link_command(agent["command"]):
            PrintUtils.print_warn(
                "未能自动确认 {} 命令路径，请检查 npm 全局 bin 目录".format(
                    agent["command"]
                )
            )

        verify = self._run_cmd(
            "{} --version".format(agent["command"]),
            20,
            "验证 {} 版本...".format(agent["name"]),
        )
        if self._code(verify) != 0:
            verify = self._run_cmd(
                "sudo npm list -g {} --depth=0".format(agent["package"]),
                20,
                "验证 npm 全局安装状态...",
            )
            if self._code(verify) != 0:
                PrintUtils.print_error("{} 验证失败".format(agent["name"]))
                return False

        PrintUtils.print_success("{} 安装完成".format(agent["name"]))
        PrintUtils.print_info("启动命令: {}".format(agent["command"]))
        PrintUtils.print_info(agent["login_hint"])
        return True

    def _uninstall_agent(self, key):
        agent = self.AGENTS[key]
        self._run_cmd(
            "sudo rm -f /usr/local/bin/{}".format(agent["command"]),
            10,
            "清理 {} 命令链接...".format(agent["command"]),
        )
        result = self._run_cmd(
            "sudo npm uninstall -g {}".format(agent["package"]),
            180,
            "卸载 {} ...".format(agent["name"]),
        )
        if self._code(result) != 0:
            PrintUtils.print_error("{} 卸载失败".format(agent["name"]))
            return False
        PrintUtils.print_success("{} 卸载完成".format(agent["name"]))
        return True

    def _choose_agent_keys(self, title):
        choices = {
            1: "OpenAI Codex CLI",
            2: "Claude Code",
            3: "GitHub Copilot CLI",
            4: "全部",
        }
        code, _ = ChooseTask(choices, title, False).run()
        if code == 1:
            return ["codex"]
        if code == 2:
            return ["claude"]
        if code == 3:
            return ["copilot"]
        if code == 4:
            return ["codex", "claude", "copilot"]
        return []

    def run(self):
        actions = {
            1: "安装/更新",
            2: "卸载",
        }
        action, _ = ChooseTask(actions, "请选择操作:", False).run()
        if action == 1:
            keys = self._choose_agent_keys("请选择要安装/更新的 AI 编程助手:")
            if len(keys) == 0:
                PrintUtils.print_warn("已取消安装")
                return False
            ok = True
            for key in keys:
                if not self._install_agent(key):
                    ok = False
            return ok
        if action == 2:
            keys = self._choose_agent_keys("请选择要卸载的 AI 编程助手:")
            if len(keys) == 0:
                PrintUtils.print_warn("已取消卸载")
                return False
            ok = True
            for key in keys:
                if not self._uninstall_agent(key):
                    ok = False
            return ok

        PrintUtils.print_warn("已取消操作")
        return False
