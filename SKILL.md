---
name: zhizai-openclaw
version: 1.0.2
description: |
  用自然语言操作智在记录开放 API：做成笔记（录音/文档/图片/链接/文字）、列表过滤、打开纪要/转写、改删与等待处理、场景与知识卡、笔记集查询与归档、问小智语义问答、周报/复盘模版成文。
  用户说做成笔记、最近有哪些、打开这条、用会议纪要场景、等它处理完、找找关于、放到笔记集、写周报、我的笔记集、配置 ZHIZAI_REC_API_KEY 时使用。
  真实请求直调开放 API。雪花 ID 当字符串。基准 ZHIZAI_BASE_URL；鉴权 Header 直接传 Key（无 Bearer）。
  仓库：https://github.com/BoteAI/zhizai-openclaw
metadata:
  openclaw:
    emoji: "📒"
    requires: {}
    optionalEnv:
      - ZHIZAI_REC_API_KEY
      - ZHIZAI_APP_ID
---

# 智在记录

本 Skill **直接调用开放 API**（`Authorization: <ZHIZAI_REC_API_KEY>`，不要加 Bearer）。组合必须按序做完，禁止把名称当 ID。

只调用本 Skill 列出的接口。不要调用团队、消息、录音卡用量、口令换 Key、实时转写、声纹、分片 ASR，也不要把视频做成笔记。

## 能力与外部影响

- 调用 `https://openapi.zzjilu.com/api/v1`，读写当前 API Key 对应账号数据。
- 新建/编辑/删除笔记、归档到笔记集会改远端数据；删除必须先确认。
- 限流最高 **2 次/秒**；连续调用间隔 ≥500ms。
- 不会自行安装其他软件、下载覆盖本 Skill，或泄露完整 Key。

## 执行约定（必须先读）

每条用户说法是 **单步** 或 **组合 N 步**。组合必须按 ①②③ 做完，缺一步即错。中途失败即停，不要跳步、不要猜 ID。

| 标记 | 本 Skill 怎么做 |
|---|---|
| 单步 | 只走一条对外闭环（例如一次列表，或一次「做成笔记」）。 |
| 单步（内部多接口） | 对外仍是一次「做成笔记」或一次「问小智」。内部才上传 + 创建 + 轮询，或先会话再 SSE。**不要**停在「已上传」或把创建成功说成转写完成。 |
| 组合 N 步 | 必须先查真实 ID，再写/读。名称未解析前禁止写操作。 |
| 附加参数 | 不能单独调接口，必须并进同一次创建。 |

**会话里已有的 ID 才能跳过查询。** 本轮已拿到的 `noteId` / `knowledgeId` / `directoryId`（`catalogId`）/ `sceneId` / `chatId`+`contextId` 可直接用。用户只说名称、会话又没有对应 ID，就必须先查。禁止把名称当成 ID，禁止编造雪花 ID。ID 全程当字符串传递。

名称 → ID：

| 用户说的 | 先调 | 得到 |
|---|---|---|
| 笔记 / 「这条纪要」/ 标题 | `POST /note/queryNoteList`（`title`），零条停、多条让用户选 | `noteId` |
| 笔记集名称 | `POST /note/queryNoteKnowledge`（别人分享的再 `queryNoteKnowledgeEmpower`），按名称匹配 | `knowledgeId` |
| 目录名称 | 先有 `knowledgeId`，再 `POST /note/queryKnowledgeCatalog`，按 `catalogName` 匹配 | `directoryId` / `catalogId` |
| 总结场景名称 | `GET /note/queryMySceneList` 或 `GET /note/queryInnerSceneList`，按名称匹配 | `sceneId` |

创建成功不等于转写/总结完成。只有 `note_state=completed`（或用户明确说不用等）才能宣称已完成。

## 意图分流（不要混用）

| 用户说法 | 走哪条 | 不要走 |
|---|---|---|
| 「最近有哪些 / 我的录音 / 标题带经营分析 / 这个月的」 | 列表 `queryNoteList` | 问小智 |
| 「打开这条 / 看纪要 / 只要转写」 | 无 ID 先列表，再 `querySingleNoteDetail`；只要原文用 `content`，只要纪要用 `summary` | 把 summary 当原文 |
| 「做成笔记 / 把文件生成笔记 / 记一条 / 收藏链接」 | 一次「做成笔记」闭环（见下） | 只上传就停；追问类型 |
| 「用某某场景做成笔记」 | ① 查 `sceneId` ② 做成笔记并带 `sceneId` | 把场景名当 ID |
| 「放到某某笔记集 / 建目录 / 移笔记」 | ① 名称先查 `knowledgeId`/`directoryId` ② `createNote` 带归档字段，或 `moveNotesToKnowledge` | 把名称当 ID；假装已归档 |
| 「给这段话出个总结」（用户给了文字，不是某条笔记） | `POST /note/createTextNoteSummary` | 问小智；某条笔记的 summary |
| 「本周会议总结 / 写周报 / 按结构成文」 | **动态模版管线**：先 `queryStandardInputOutputByCommand`，再填真实笔记 | 当成单条笔记的 `summary`；问小智 |
| 「找找关于… / 在笔记集里问 / 待办有哪些」且要**语义问答** | **问小智**：先 `createXiaozhiSession` 再 `xiaozhiChat`。不要用列表冒充 | `queryNoteList.title` 冒充语义搜索 |
| 「改标题 / 改摘要 / 改总结」 | **必须先有 `noteId`**：无 ID 则 `queryNoteList` 按标题选定，再 `POST /note/updateNoteInfo`，再详情读回 | 没有 `noteId` 就调更新；把标题当 ID |

## 做成笔记（对外一次，内部可多接口）

用户不必说明笔记类型。没点名类型时必须按输入判断，**不要追问「这是录音还是文档」**：

| 用户给了什么 | 判定 | 内部 |
|---|---|---|
| 本地音频 `mp3/wav/m4a/aac/ogg/flac/amr/opus` | 录音 | 上传 → `createNote` `noteType=voice`（途径默认 `offlineImport`，不要追问） |
| 本地图片 `jpg/jpeg/png/gif/webp/bmp/heic` | 图片 | 上传 → `createNote` `noteType=image`；多张合成一条 |
| 本地视频 `mp4/mov/avi/mkv/webm/m4v` | 不能做成笔记 | 停并说明。用户只要「上传」则只 `uploadSingleFile`。禁止当成录音 |
| 本地文档 `pdf/doc/docx/ppt/pptx/xls/xlsx/txt/md` | 文档 | 上传 → `createNote` `noteType=document`；`title` 优先于文件名 |
| `http://` 或 `https://` URL | 链接 | `createNote` `noteType=link` |
| 没有文件、只有文字 | 文字 | `createNote` `noteType=text` |
| 一份音频 + 若干图片，且用户说「附图」 | 录音带附图 | 音频作主文件；图片 ID 写入 `voiceContent.imageFileIds` |
| 无法识别的扩展名 | 不创建 | 列出可支持做成笔记的格式（录音/文档/图片） |

用户只说「上传」、没说做成笔记：只 `POST /file/uploadSingleFile`，返回 `fileId`。音频默认不压缩。

录音/文档/图片默认等待：创建后轮询 `GET /note/queryNoteStatus` 至 `completed`/`failed`/`recognizing_failed`/`analyzing_failed`，再读详情。用户说不用等则立刻返回 `noteId` 与 `note_state`。成功最低标准：非空 `noteId`。失败态展示状态，禁止自动再创建。

用户同时说「放到某某笔记集」：先解析 `knowledgeId`（及目录则 `directoryId`）。录音写入 `voiceContent.knowledgeId` / `directoryId`（不传目录或 `-1` 表示根层）；文字/图片/文档/链接创建后再 `moveNotesToKnowledge`。无效笔记集：笔记可能已创建，必须写清「已创建但未归档」。

本地路径不存在：不调上传/创建。

## 能力概览

| 用户想做什么 | 典型说法 | 本 Skill | 完成后应返回 |
|---|---|---|---|
| 做成笔记 | 「把 meeting.mp3 做成笔记」 | ✅ 上传+创建+默认等待 | `noteId`、标题、类型；完成前须 `completed` |
| 列表过滤 | 「最近有哪些录音」 | ✅ `queryNoteList` | `id`、标题、中文类型、状态、时间。空列表是成功 |
| 打开 / 纪要 / 原文 | 「打开这条」 | ✅ 无 ID 先查 | 处理中须说明 |
| 改标题 / 摘要 / 总结 | 「把某某笔记的标题改成…」 | ✅ **先查 `noteId`** 再 `updateNoteInfo`，再读回 | 没有真实 ID 禁止调用。只改传入字段 |
| 删除 / 等待 | 「删掉」「等它处理完」 | ✅ 无 ID 先查；删除先确认 | 读回或终态 |
| 指定场景后保存 | 「用会议纪要场景…」 | ✅ 先查 `sceneId` | 查不到则停 |
| 场景 / 知识卡 | 「有哪些总结场景」 | ✅ | 真实 ID/名称 |
| 笔记集查询 | 「我的笔记集」「打开工作笔记集」 | ✅ 名称先 list | 名称、`knowledgeId`、集内条目 |
| 归档 / 建集 / 建目录 / 移笔记 | 「放到工作笔记集」 | ✅ 名称先查 ID | 归档成功或「已创建但未归档」 |
| 问小智语义检索 | 「找找关于支付的」 | ✅ 先会话再 SSE | 流式回答；范围内无内容如实说 |
| 写周报 / 复盘 | 「按周报结构总结本周会议」 | ✅ 动态模版管线 | 按模版填真实笔记 |
| 文字流式总结 | 「给这段话出个总结」 | ✅ SSE | 结束即完成 |
| 按 fileId 取回文件 | 「把这个文件下载下来」 | ✅ `GET /file/getFile/{fileId}` | 二进制或跟随重定向后落盘；404=不存在；笔记录音改走下载音频 |
| 连接 | 「配置 Key」 | ✅ API Key | 探活 `queryNoteList` pageSize=1 |

不要要求用户记接口路径。

## 哪些必须组合

| 用户说法 | 最少步数 | 本 Skill 顺序 |
|---|---|---|
| 「用会议纪要场景，把录音做成笔记」 | 2 | ① 查 `sceneId` ② 做成笔记（带 `sceneId`，默认等待） |
| 「打开这条 / 看纪要 / 转写 / 删除 / 下载音频」，没给 ID | 2 | ① 按标题查 `noteId` ② 再详情/删除/下音频 |
| 「把某某笔记的标题/摘要/总结改掉」 | 2～3 | ① 无 `noteId` 先 `queryNoteList` 按标题选定（零条停、多条让用户选）② `POST /note/updateNoteInfo`（`noteId` 必填）③ `querySingleNoteDetail` 读回。没有 ID 禁止调用 |
| 「打开某某笔记集 / 看某目录」 | 2～3 | ① list 得 `knowledgeId` ② 若点目录再 `queryKnowledgeCatalog` ③ 详情 |
| 「放到工作笔记集」再保存 | 2～3 | ① 查 `knowledgeId`（及目录） ② 做成笔记带 `knowledgeId`/`directoryId` ③ 默认等待 |
| 「新建笔记集 / 建目录 / 把笔记放进去」 | 2～4 | ① 名称先查或创建得 ID ② `addKnowledgeCatalog` / `moveNotesToKnowledge`；删目录先确认 |
| 「找找关于… / 在某集里问」 | 2～4 | ① 名称先查范围 ID（若有） ② `createXiaozhiSession` ③ `xiaozhiChat` ④ 有引用再查、结束后清缓存 |
| 「上次那条还在转，好了叫我」 | 2 | ① 轮询 status ② 仅 `completed` 后再读详情 |
| 「把这段追加到刚才那条会」（无 `noteId`） | 2～3 | ① 按标题选定 ② 创建 `appendNoteId` ③ 默认等待 |
| 「按周报结构总结本周会议」 | 3 | ① `queryStandardInputOutputByCommand` ② `queryNoteList`（必要时详情）③ 按模版填真实笔记 |

其余（只上传、只做成笔记、只列笔记、只列笔记集、只创建会话）才是单步。

## 首次连接

1. 检查 `ZHIZAI_REC_API_KEY` 非空。未配置：只提示配置，并推荐 [智在记录开发者](https://www.zzjilu.com/pc/developer)；不调业务接口。
2. 无写入探活：`POST /note/queryNoteList`，`pageNum=1`、`pageSize=1`。`resultCode=="0"` 才可说已连接。
3. 只有用户同意时才创建测试笔记；必须返回真实 `id`、标题与 `note_state`。
4. 本会话已成功调用过任一接口后，可不再重复强调 Key 检查。

常量：`ZHIZAI_BASE_URL` = `https://openapi.zzjilu.com/api/v1`。
如接口返回「缺失应用 ID」，补 Header `APP-ID`：优先用最近一次 `uploadSingleFile` 返回的 `resultObject.appId`；没有上传时用环境变量 `ZHIZAI_APP_ID`。**不要编造**。`downloadNoteAudio`、`moveNotesToKnowledge` 缺 `APP-ID` 时可能报该错误。

## 每次任务的执行闭环

1. **理解目标**：做成笔记 / 只上传 / 列表 / 打开 / 改删 / 归档 / 问小智 / 模版成文。
2. **解析 ID**：名称先查；零条停、多条让用户选。
3. **读取本次接口协议**：只打开下面清单里、本次用到的文件。
4. **按序调开放 API**：JSON 用 `application/json`；上传用 `multipart/form-data`；遵守限流。做成笔记、问小智不要对用户拆步。
5. **判断结果**：先看 HTTP（400/401/406=无权限），再看 `resultCode=="0"`。未 `completed` 不得说总结已完成。下载看 HTTP 与 `Content-Type`。
6. **必要时复读**：更新、删除后再查确认。
7. **回复用户**：先结论；失败说明停在哪一步，不泄露 Key/`stack`。

## 接口协议

按意图打开对应文件，字段以其中「接口协议」为准。这些文件里出现的路径，就是本 Skill 允许调用的全部接口：

- 场景执行顺序：[`references/scenarios.md`](references/scenarios.md)
- 鉴权与探活：[`references/auth.md`](references/auth.md)
- 笔记做成/列表/详情/等待/改删/上传下载/动态模版：[`references/note.md`](references/note.md)
- 问小智会话与 SSE：[`references/xiaozhi.md`](references/xiaozhi.md)
- 场景与知识卡：[`references/scene.md`](references/scene.md)
- 笔记集查询与写入：[`references/knowledge.md`](references/knowledge.md)

## 结果呈现标准

- **做成笔记**：真实 `noteId`、标题、类型、`note_state`。处理中不要伪造成文完成。
- **列表**：`id`、`title`、中文类型、`note_state`、`create_time`；有 `summary` 用总结否则 `abstract`。空列表是成功。
- **详情**：只要原文用 `content`，只要纪要用 `summary`。用户没要分享时不要主动短链（需要时才传 `withShortUrl=true`）。
- **问小智**：拼接 SSE `text`；`notData`/`error` 用原文。不要编造检索结果。
- **模版成文**：按最终模版填真实笔记；缺失标「未提及」。
- **进度**：只报告系统阶段。
- **失败**：短句 + 下一步；禁止展示完整 Key、`stack`、未脱敏 `errorInfos`。

`note_type`：`text` 文本 / `voice` 录音 / `document` 文档 / `link` 链接 / `image` 图片 / `video` 视频 / `knowCard` 知识卡片。

## 统一规则

- 真实操作只走开放 API；请求字段以本次打开的协议文件为准。
- `resultCode != "0"` 一律失败；优先用 `resultMsg`。
- ID、fileId 按返回原样传递，当字符串。
- 修改路径 **`POST /note/updateNoteInfo`**（不是 `updateNote`）；摘要字段 `abstractContent`。**`noteId` 必填**：会话没有则先 `queryNoteList` 拿到真实 ID，禁止空传、禁止把标题当 ID。
- 删除笔记、删目录、覆盖性修改须先确认。
- 群聊不主动展开私密全文与手机号。

## 常见恢复方式

- HTTP 400/401/406：检查 `ZHIZAI_REC_API_KEY`，不回显 Header。HTTP 401 且 body 为空：该 Key **未勾选**当前接口，让用户到开发者后台勾选。`resultMsg` 含「请关联API」时同样处理。
- `GET /file/getFile/{fileId}`：成功是二进制或跟随 3xx 后再落盘。HTTP 404=文件不存在。HTTP 401 空 body=Key 未勾选，引导勾选，不要改生产、不要假装已下载。
- 「缺失应用 ID」：补 Header `APP-ID`（来自上传回包 `appId` 或 `ZHIZAI_APP_ID`）后重试 `downloadNoteAudio` / `moveNotesToKnowledge`，不要改接口路径。
- 「有哪些总结场景」：`queryInnerSceneList` 的 `resultObject` 是**分类 Map**（另有 `groupInfo`），必须遍历各分类数组取 `id` / `scene_name`，不要当普通 list。
- 详情 `resultCode=0` 但 `resultObject.id` 为空：按不存在处理，不要说已打开。
- 下载录音 / 按 fileId 取回：成功才是二进制流，或跟随 3xx 重定向后再保存。HTTP 404=文件不存在。若返回 JSON，如实失败，不要假装已保存到本地。
- 名称查不到：停，不要空传 `sceneId` / `knowledgeId`。
- 处理失败：展示状态，禁止自动再创建。
- 问小智缺 `chatId`/`contextId`：先创建会话，不要在问答接口里自动补。
- 限流：等待后重试。
- 网络中断或结果不确定：只查询核验，不自动重复写入。
