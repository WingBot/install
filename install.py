# -*- coding: utf-8 -*-
import importlib
import os

INSTALL_TMP_DIR = os.environ.get("OFFICE_INSTALL_TMP_DIR", "/tmp/office_install")
url_prefix = os.environ.get("INSTALL_BASE_URL", "https://install.example.com/")
base_url = os.path.join(url_prefix, "tools/base.py")
translator_url = os.path.join(url_prefix, "tools/translation/translator.py")

INSTALL_ROS = 0  # 安装ROS相关
INSTALL_SOFTWARE = 1  # 安装软件
CONFIG_TOOL = 2  # 配置相关
INSTALL_AI = 3  # AI相关
INSTALL_NETWORK = 4  # 网络工具
INSTALL_OFFICE = 5  # 自有办公软件


tools_type_map = {
    INSTALL_ROS: "ROS相关",
    INSTALL_AI: "AI板块",
    INSTALL_SOFTWARE: "常用软件",
    CONFIG_TOOL: "配置工具",
    INSTALL_NETWORK: "网络工具",
    INSTALL_OFFICE: "办公软件",
}


tools = {
    1: {
        "tip": "一键安装(推荐):ROS(支持ROS/ROS2,树莓派Jetson)",
        "type": INSTALL_ROS,
        "tool": "tools/tool_install_ros.py",
        "dep": [4, 5],
    },
    2: {
        "tip": "一键安装:github桌面版(小鱼常用的github客户端)",
        "type": INSTALL_SOFTWARE,
        "tool": "tools/tool_install_github_desktop.py",
        "dep": [],
    },
    3: {
        "tip": "一键安装:rosdep(小鱼的rosdepc,又快又好用)",
        "type": INSTALL_ROS,
        "tool": "tools/tool_config_rosdep.py",
        "dep": [],
    },
    4: {
        "tip": "一键配置:ROS环境(快速更新ROS环境设置,自动生成环境选择)",
        "type": INSTALL_ROS,
        "tool": "tools/tool_config_rosenv.py",
        "dep": [],
    },
    5: {
        "tip": "一键配置:系统源(更换系统源,支持全版本Ubuntu系统)",
        "type": CONFIG_TOOL,
        "tool": "tools/tool_config_system_source.py",
        "dep": [1],
    },
    6: {
        "tip": "一键安装:NodeJs环境",
        "type": INSTALL_AI,
        "tool": "tools/tool_install_nodejs.py",
        "dep": [],
    },
    7: {
        "tip": "一键安装:VsCode开发工具",
        "type": INSTALL_SOFTWARE,
        "tool": "tools/tool_install_vscode.py",
        "dep": [],
    },
    8: {
        "tip": "一键安装:Docker",
        "type": INSTALL_SOFTWARE,
        "tool": "tools/tool_install_docker.py",
        "dep": [],
    },
    9: {
        "tip": "一键安装:Cartographer(18 20测试通过,16未测. updateTime 20240125)",
        "type": INSTALL_ROS,
        "tool": "tools/tool_install_cartographer.py",
        "dep": [3],
    },
    10: {
        "tip": "一键安装:微信(可以在Linux上使用的微信)",
        "type": INSTALL_SOFTWARE,
        "tool": "tools/tool_install_wechat.py",
        "dep": [8],
    },
    11: {
        "tip": "一键安装:ROS Docker版(支持所有版本ROS/ROS2)",
        "type": INSTALL_ROS,
        "tool": "tools/tool_install_ros_with_docker.py",
        "dep": [7, 8],
    },
    12: {
        "tip": "一键安装:PlateformIO MicroROS开发环境(支持Fishbot)",
        "type": INSTALL_SOFTWARE,
        "tool": "tools/tool_install_micros_fishbot_env.py",
        "dep": [],
    },
    13: {
        "tip": "一键配置:python国内源",
        "type": CONFIG_TOOL,
        "tool": "tools/tool_config_python_source.py",
        "dep": [],
    },
    14: {
        "tip": "一键安装:科学上网代理工具",
        "type": INSTALL_AI,
        "tool": "tools/tool_install_proxy_tool.py",
        "dep": [8],
    },
    15: {
        "tip": "一键安装：QQ for Linux",
        "type": INSTALL_SOFTWARE,
        "tool": "tools/tool_install_qq.py",
        "dep": [],
    },
    16: {
        "tip": "一键安装：系统自带ROS (！！警告！！仅供特殊情况下使用)",
        "type": INSTALL_ROS,
        "tool": "tools/tool_install_ros1_systemdefault.py",
        "dep": [5],
    },
    17: {
        "tip": "一键配置: Docker代理(支持VPN+代理服务两种模式)",
        "type": CONFIG_TOOL,
        "tool": "tools/tool_config_docker_proxy.py",
        "dep": [],
    },
    18: {
        "tip": "一键安装/卸载:OpenCode(AI编程助手)",
        "type": INSTALL_AI,
        "tool": "tools/tool_install_opencode.py",
        "dep": [6],
    },
    19: {
        "tip": "一键安装:基础工具包(curl/wget/git/unzip等)",
        "type": CONFIG_TOOL,
        "tool": "tools/tool_install_basic_tools.py",
        "dep": [],
    },
    20: {
        "tip": "一键管理:RustDesk远程控制(安装/修复配置/卸载)",
        "type": INSTALL_OFFICE,
        "tool": "tools/tool_install_rustdesk.py",
        "dep": [19],
    },
    22: {
        "tip": "一键安装并配置:frpc SSH内网穿透",
        "type": INSTALL_NETWORK,
        "tool": "tools/tool_install_frpc.py",
        "dep": [19],
    },
    23: {
        "tip": "一键安装并配置:搜狗输入法",
        "type": INSTALL_OFFICE,
        "tool": "tools/tool_install_sogou_input.py",
        "dep": [19],
    },
    24: {
        "tip": "一键安装并配置:Zellij终端复用器",
        "type": INSTALL_SOFTWARE,
        "tool": "tools/tool_install_zellij.py",
        "dep": [19],
    },
    25: {
        "tip": "一键安装并配置:Oh My Zsh",
        "type": CONFIG_TOOL,
        "tool": "tools/tool_install_ohmyzsh.py",
        "dep": [19],
    },
    26: {
        "tip": "一键安装:Google Chrome最新版",
        "type": INSTALL_SOFTWARE,
        "tool": "tools/tool_install_chrome.py",
        "dep": [19],
    },
    27: {
        "tip": "一键安装/卸载:AI编程助手(Codex/Claude Code/Copilot)",
        "type": INSTALL_AI,
        "tool": "tools/tool_install_ai_code_agents.py",
        "dep": [6],
    },
    28: {
        "tip": "一键安装:办公套件(Zotero/Obsidian/WPS/字体)",
        "type": INSTALL_OFFICE,
        "tool": "tools/tool_install_office_suite.py",
        "dep": [19],
    },
    29: {
        "tip": "一键安装:截图和录屏工具(Flameshot/Peek/ffmpeg)",
        "type": INSTALL_SOFTWARE,
        "tool": "tools/tool_install_desktop_capture.py",
        "dep": [19],
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
        code != 0
        and os.environ.get("GITHUB_ACTIONS") != "true"
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
