# 个人资料管理插件 (IM Profile)

![:name](https://count.getloli.com/@astrbot_plugin_im_profile?name=astrbot_plugin_im_profile&theme=miku&padding=7&offset=0&align=top&scale=1&pixelated=1&darkmode=auto)

## 让 Bot 可以通过 LLM Tool 管理自身资料

> [!note]
> 当前版本仅支持 QQ 平台 (`aiocqhttp` / NapCat)。

***

### 主要特性

- 支持修改 Bot 基础资料：昵称、资料签名、性别
- 支持修改 Bot 头像（远程 URL、本地文件路径、`file://`）
- 支持修改 Bot 在群内的个人群名片
- 支持查询 Bot 自身或指定 QQ 用户的头像 URL
- 头像查询工具会在可用时返回图片内容，便于支持图像输入的模型继续处理
- 支持通过配置项精细控制每个 LLM Tool 的启用状态

### LLM Tool 列表

- `im_profile_set_profile`
  - 功能：修改基础资料（昵称、资料签名、性别）
  - 参数：`nickname`、`personal_note`、`sex`
  - `sex` 支持：`male` / `female` / `unknown`（也支持常见同义词）

- `im_profile_set_avatar`
  - 功能：修改头像
  - 参数：`avatar_url`

- `im_profile_set_group_card`
  - 功能：修改群内个人群名片
  - 参数：`card`、`group_id`（可选，不填默认使用当前群）

- `im_profile_get_avatar`
  - 功能：查询头像 URL，并在可下载时返回图片内容
  - 参数：`user_id`（可选，不填默认查询 Bot 自身）

### 配置项

- `llm_tool_options`
  - 类型：`list`
  - 默认值：`["profile", "avatar", "group_card", "avatar_lookup"]`
  - 可选值：
    - `profile`：启用 `im_profile_set_profile`
    - `avatar`：启用 `im_profile_set_avatar`
    - `group_card`：启用 `im_profile_set_group_card`
    - `avatar_lookup`：启用 `im_profile_get_avatar`


### 使用示例（自然语言）

- `把你的昵称改成 AstrBot，签名改成 Hello World`
- `把你的头像改成 https://example.com/avatar.png`
- `把你的头像改成这个[图片]`
- `把你在这个群的名片改成 小助手`
- `你的头像是什么`
- `@xxxx的头像是什么`

### 注意事项

- 当前仅适配 QQ（`aiocqhttp` / NapCat），其他平台会返回不支持提示
- 修改群名片需要群上下文，或显式提供 `group_id`
- NapCat 侧权限不足时，相关接口调用可能失败

### 更新日志

#### v0.0.1

- 首个版本发布
- 提供 4 个 LLM Tool：资料修改、头像修改、群名片修改、头像查询
- 支持通过配置控制工具启用状态
