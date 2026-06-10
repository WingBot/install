# Changelog

本文记录 `office` 分支从 FishROS 安装器改造成办公软件安装器的主要提交和设计意图。

## Unreleased

### RustDesk 包选择优化

- RustDesk 安装工具优先选择 GitHub release 中当前架构对应的主线 `.deb` 包。
- 如果 release 中不存在非 `sciter` 的主线包，才回退使用 `sciter` 包。
- 这样可以避免在同时存在 Flutter 主线包和 Sciter 兼容包时，误装 `rustdesk-*-sciter.deb`。

## 97172fc - Set RustDesk permanent password

- RustDesk 安装完成后自动导入 ID/中继服务器配置。
- 自动设置固定密码，规则为：用户名首字母大写后拼接 `#2026`。
- 示例：`zzr` 对应密码 `Zzr#2026`。

## 1b685eb - Add RustDesk uninstall option

- 新增菜单项 `[6]`：卸载 RustDesk 并清理当前用户配置。
- 卸载流程包括 `apt remove`、`apt purge`、`apt autoremove` 和删除用户侧 RustDesk 配置目录。
- RustDesk 工具脚本通过菜单 `mode` 字段区分安装和卸载，避免复制两份脚本。

## bd2b0c9 - Add RustDesk installer

- 新增菜单项 `[5]`：安装并配置 RustDesk 远程控制。
- 自动识别 `amd64` / `arm64` 架构。
- 从 RustDesk GitHub 最新 release 查找对应 `.deb` 包并安装。
- 安装完成后导入预置 ID/中继服务器配置。

## 7b85775 - Document office installer testing and deployment

- README 增加异机测试说明。
- 补充局域网 HTTP、GitHub Raw、公网域名三种测试方式。
- 增加常见问题排查：默认域名、Raw 访问、局域网端口、sudo、apt 源等。

## 0e86b8f - Start office installer migration

- 将原 FishROS 安装器入口改造为办公软件安装器入口。
- 引入 `INSTALL_BASE_URL` 和 `/tmp/office_install`。
- 精简菜单，保留基础工具、微信、QQ、VS Code 等初始项。
- 新增基础工具包安装项，用于验证完整动态下载和工具执行链路。
