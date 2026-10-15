# 文档索引

## 编码 Agent

- [统一工作约定](../AGENTS.md)：MONO 口吻、功能更新公告、代码验证及文件清理规则。
- [Claude Code 入口](../CLAUDE.md)：引用统一约定，不单独维护规则。
- [MONO 原始人设](../KouriChat/data/avatars/MONO/avatar.md)：聊天角色资料；开发协作使用统一工作约定中的提炼。

## 开发与使用

- [项目说明](../README.md)：功能、安装、配置与使用。
- [核心架构](architecture.md)：线程、实例、消息队列及维护时段。
- [实例开发](instance-development.md)：新增实例、工厂注册和消息收发。
- [Steam / CS2 数据格式](../cs2_platforms/DATA_FORMAT.md)。
- [完美平台接入](../cs2_platforms/cs2_pw/README.md)。
- [KoriChat 使用文档](KoriChat%20使用文档.md) 与 [指令说明](KoriChat%20指令说明.md)。
- [CS2 视频插件](../Plugins/CS2Video/README.md)。
- [灾害预警插件](../Plugins/disaster_warning/README.md)。

## 远程管理 Agent 与 Web 面板

这里的 Agent 指 `agent/client.py` 运行的项目服务，与 Codex 等编码 Agent 区分。

- [Web 使用与 Agent 连接](../web/README.md)：部署入口、连接参数和配置。
- [运维说明](../web/OPS.md)：启停、远程部署与排障。
- [需求与接口参考](../web/REQUIREMENTS.md)：功能及接口约定；当前接口以运行服务的 `/docs` 和源代码为准。

项目约定只在 `AGENTS.md` 维护；使用说明与实现细节放在对应功能文档。已被实现替代且无引用的一次性设计稿可清理，仍在使用的接口、运维和人设文档继续保留。
