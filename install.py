# -*- coding: utf-8 -*-
import importlib
import os

INSTALL_TMP_DIR = os.environ.get("OFFICE_INSTALL_TMP_DIR", "/tmp/office_install")
url_prefix = os.environ.get("INSTALL_BASE_URL", "https://install.example.com/")
base_url = os.path.join(url_prefix, "tools/base.py")
translator_url = os.path.join(url_prefix, "tools/translation/translator.py")

INSTALL_OFFICE = 0
INSTALL_DEV = 1
CONFIG_TOOL = 2
INSTALL_NETWORK = 3

tools_type_map = {
    INSTALL_OFFICE: "办公软件",
    INSTALL_DEV: "开发工具",
    CONFIG_TOOL: "配置工具",
    INSTALL_NETWORK: "网络工具",
}


tools = {
    1: {
        "tip": "一键安装:基础工具包(curl/wget/git/unzip等)",
        "type": CONFIG_TOOL,
        "tool": "tools/tool_install_basic_tools.py",
        "dep": [],
    },
    2: {
        "tip": "一键安装:微信(可以在Linux上使用的微信)",
        "type": INSTALL_OFFICE,
        "tool": "tools/tool_install_wechat.py",
        "dep": [],
    },
    3: {
        "tip": "一键安装:QQ for Linux",
        "type": INSTALL_OFFICE,
        "tool": "tools/tool_install_qq.py",
        "dep": [],
    },
    4: {
        "tip": "一键安装:VS Code",
        "type": INSTALL_DEV,
        "tool": "tools/tool_install_vscode.py",
        "dep": [],
    },
    5: {
        "tip": "一键安装并配置:RustDesk远程控制",
        "type": INSTALL_OFFICE,
        "tool": "tools/tool_install_rustdesk.py",
        "dep": [1],
        "mode": "install",
    },
    6: {
        "tip": "一键卸载:RustDesk远程控制(含用户配置)",
        "type": CONFIG_TOOL,
        "tool": "tools/tool_install_rustdesk.py",
        "dep": [],
        "mode": "uninstall",
    },
    7: {
        "tip": "一键安装并配置:frpc SSH内网穿透",
        "type": INSTALL_NETWORK,
        "tool": "tools/tool_install_frpc.py",
        "dep": [1],
    },
}


# 创建用于存储不同类型工具的字典，按目录顺序展示
tool_categories = {tool_type: {} for tool_type in tools_type_map}

# 遍历tools字典，根据type值进行分类
for tool_id, tool_info in tools.items():
    tool_type = tool_info["type"]
    tool_categories[tool_type][tool_id] = tool_info

# 清理空目录，避免展示无工具分类
tool_categories = {k: v for k, v in tool_categories.items() if v}

tracking = None


def download_runtime_files(url_prefix):
    os.system("mkdir -p {}/tools/translation/assets".format(INSTALL_TMP_DIR))
    if not url_prefix:
        return
    print("Downloading: {}".format(base_url))
    os.system(
        "wget --show-progress --progress=bar:force:noscroll {} -O {}/{} --no-check-certificate".format(
            base_url, INSTALL_TMP_DIR, base_url.replace(url_prefix, "")
        )
    )
    print("Downloading: {}".format(translator_url))
    os.system(
        "wget --show-progress --progress=bar:force:noscroll {} -O {}/{} --no-check-certificate".format(
            translator_url, INSTALL_TMP_DIR, translator_url.replace(url_prefix, "")
        )
    )


def main():
    global tracking

    url_prefix = os.environ.get("INSTALL_BASE_URL", "https://install.example.com/")
    download_runtime_files(url_prefix)

    from tools.base import (
        CmdTask,
        FileUtils,
        PrintUtils,
        ChooseWithCategoriesTask,
        Tracking,
    )
    from tools.base import config_helper, download_tools, encoding_utf8, run_tool_file, tr

    importlib.import_module("tools.translation.translator").Linguist()
    from tools.base import tr
    import copy

    tracking = copy.copy(Tracking)

    PrintUtils.print_success(tr.tr("已为您切换语言至当前所在国家语言:") + tr.lang)

    # check base config
    if not encoding_utf8:
        print("Your system encoding not support, will install some packages...")
        CmdTask("sudo apt-get install language-pack-zh-hans -y", 0).run()
        CmdTask("sudo apt-get install apt-transport-https -y", 0).run()
        FileUtils.append("/etc/profile", 'export LANG="zh_CN.UTF-8"')
        print("Finish! Please Try Again!")
        return False
    PrintUtils.print_success(tr.tr("基础检查通过..."))

    book = tr.tr("""
        ----------------------------------------------------------------------
                 Office Install
                 办公软件与基础工具一键安装器
        ----------------------------------------------------------------------""")

    tip = tr.tr("""===============================================================================
======欢迎使用办公软件一键安装工具，按需选择菜单项开始安装。=======
======项目地址：https://github.com/WingBot/install =======
===============================================================================
    """)
    PrintUtils.print_delay(tip, 0.001)
    PrintUtils.print_delay(book, 0.001)

    code, result = ChooseWithCategoriesTask(
        tool_categories,
        tips=tr.tr("---请选择需要安装或配置的项目---"),
        categories=tools_type_map,
    ).run()
    if code == 0:
        PrintUtils().print_success(tr.tr("已退出安装器。"))
    else:
        if url_prefix:
            download_tools(code, tools, url_prefix)
        tool = run_tool_file(tools[code]["tool"].replace("/", "."), authorun=False)
        if hasattr(tool, "set_mode"):
            tool.set_mode(tools[code].get("mode", "install"))
        if tool.init() != False and tool.run() != False:
            tool.uninit()

    if (
        os.environ.get("GITHUB_ACTIONS") != "true"
        and os.environ.get("OFFICE_INSTALL_CONFIG") is None
    ):
        config_helper.gen_config_file()


if __name__ == "__main__":
    run_exc = []

    try:
        main()
    except Exception:
        import traceback

        print("\r\n检测到程序发生异常退出，请携带如下内容进行反馈\n\n")
        print("标题：使用办公软件一键安装过程中遇到程序崩溃")
        print("```")
        traceback.print_exc()
        run_exc.append(traceback.format_exc())
        print("```")
        print("本次运行详细日志文件已保存至 /tmp/office_install.log")

    try:
        with open("/tmp/office_install.log", "w", encoding="utf-8") as f:
            for exec_text in run_exc:
                print(exec_text, file=f)
            if tracking is not None:
                for text, end in tracking.logs:
                    print(text, file=f, end=end)
                for text in tracking.err_logs:
                    print(text, file=f)
    except Exception:
        pass
