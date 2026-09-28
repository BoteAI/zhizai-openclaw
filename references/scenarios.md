# 智在记录 · 场景执行

直调开放 API。组合按序做完，禁止把名称当 ID。

标记：

| 落地 | 含义 |
|---|---|
| ✅ | 本 Skill 按下列 API 顺序即可完成 |
| ⚠️ | 可部分完成，必须把做不到的部分说清 |
| ❌ | 开放 API 无能力，停并说明；禁止冒充 |

机器调用间隔 ≥500ms。雪花 ID 当字符串。

对用户：可用 `resultMsg` 短句；禁止展示完整 Key、`stack`、未脱敏 `errorInfos`。限流 ≤2 次/秒。

`ZHIZAI_BASE_URL` = `https://openapi.zzjilu.com/api/v1`。Header：`Authorization: ${ZHIZAI_REC_API_KEY}`（无 Bearer）。

## 做成笔记：内部闭环（对外单步）

异步类型（录音/图片/文档）默认走完整闭环；用户说不用等则停在创建成功。本地视频不能做成笔记：停并说明；用户只要「上传」则只 `uploadSingleFile`。禁止当成录音。

1. 本地路径存在且扩展名可识别，否则失败、不调接口。视频扩展名不创建。
2. 需要文件：`POST /file/uploadSingleFile`（用户说压缩才 `compressFile=true`；音频不要压）。
3. 创建：文字 `noteType=text` / 链接 `link` / 图片 `image` / 文档 `document` / 录音 `voice` → `POST /note/createNote`
4. 默认等待：轮询 `GET /note/queryNoteStatus?noteId=` 至 `completed` 或 `failed` / `*_failed`。
5. 仅 `completed` 后 `GET /note/querySingleNoteDetail?noteId=` 再给纪要/转写。

做成笔记成功最低标准：非空 `noteId`。`failed` 禁止自动再创建。

创建附加字段（必须并进同一次 `createNote`，不能单独调）：

| 用户说法 | 字段 |
|---|---|
| 录制起止与时长 | `voiceContent.recStartTime` / `recEndTime` / `duration`（录制时间，不是会议排期；时长单位秒） |
| 录音途径 | `voiceContent.recordingSource`：`realtime` / `phoneInternal` / `offlineImport`。未指定默认 `offlineImport` |
| 定位 | `latitude` / `longitude` |
| 随手备注 | `voiceContent.text`（≠ AI 总结） |
| 追加到已有会 | `voiceContent.appendNoteId`（必须是真实 `noteId`） |
| 用某某场景 | `sceneId`（必须先列表匹配；查不到则停） |
| 放到某某笔记集 | `voiceContent.knowledgeId` / `directoryId`（名称先查；不传目录或 `-1` 为根层） |

类型按扩展名判定。用户指定了类型以用户为准。

---

## 文件

| 功能 | 落地 | 用户说法 | Skill 执行 | 预期 |
|---|---|---|---|---|
| 只上传音频/图片/文档/视频 | ✅ | 「上传这个录音 meeting.mp3」 | `POST /file/uploadSingleFile` | 返回 `fileId`。不是笔记已生成 |
| 压缩后存储 | ✅ | 「压缩后再存」 | 同上，`compressFile=true` | 音频不建议开 |
| 按 fileId 取回 | ✅ | 「把这个文件下载下来」且只有 `fileId` | `GET /file/getFile/{fileId}`（跟随重定向） | 二进制或跳转后落盘。HTTP 404=文件不存在。笔记录音原文件改走「下载音频」 |

---

## 创建笔记

| 功能 | 落地 | 用户说法 | Skill 执行 | 预期 |
|---|---|---|---|---|
| 按文件自动生成 | ✅ | 「将这个文件生成一个笔记」 | 做成笔记闭环 + 默认等待 | 按扩展名判定。返回类型、`noteId`、标题 |
| 导入录音 | ✅ | 「把 meeting.mp3 做成笔记」 | 闭环 `voice`；标题可写入创建 | 途径默认离线导入，不要追问 |
| 只创建、不等待 | ✅ | 「先不要等转写」 | 闭环到 `createNote` 即停 | 返回 `noteId`、`note_state`；总结可能空 |
| 录音附图 | ✅ | 「录音里再附上这几张图」 | 音频主文件 + 图片上传进 `imageFileIds` | 不要拆成两条笔记 |
| 文字 | ✅ | 「记一条：明天交周报」 | `createNote` text | 长文避免命令行截断，用请求 body |
| 链接 | ✅ | 「收藏 https://…」 | `createNote` link | URL 不要当文字 |
| 图片 | ✅ | 「把这几张图做成笔记」 | 多图一条 `image` + 等待 | OCR/总结完成前不宣称完成 |
| 文档 | ✅ | 「把方案.pdf 做成笔记」 | `document`；title 优先文件名 | 等待完成 |
| 指定场景后保存 | ✅ 组合 2 | 「用会议纪要场景，把录音做成笔记」 | ① `queryMySceneList` 或 `queryInnerSceneList` 匹配 ② 做成笔记带 `sceneId` 并等待 | 查不到则停，不要空传 |
| 保存时归档到笔记集 | ✅ 组合 2～3 | 「把录音放到工作笔记集」 | ① 查 `knowledgeId`（及目录则 `queryKnowledgeCatalog`） ② 做成笔记带 `knowledgeId`/`directoryId` 并等待 | 无效笔记集：笔记可能已创建，必须写清「已创建但未归档」 |
| 追加到已有笔记 | ✅ 组合 1～3 | 「追加到刚才那条会」 | 无 `noteId`：先 `queryNoteList` title 选定；再 `createNote` `appendNoteId` + 等待 | 不要新建一条无关笔记 |
| 类型无法识别 | ✅ 失败 | 扩展名不支持 | 不创建 | 列出可支持格式 |

---

## 查询笔记

列表过滤不是语义搜索。没有 `noteId` 不能打开/改删/等待/下音频。

| 功能 | 落地 | 用户说法 | Skill 执行 | 预期 |
|---|---|---|---|---|
| 最近 / 类型 / 标题 / 摘要 / 时间 / 翻页 | ✅ | 「最近有哪些笔记」等 | `POST /note/queryNoteList`：`noteType` / `title` / `abstractContent` / `summary` / `content` / `startTime` / `endTime` / `pageNum` / `pageSize` | 空列表是成功。「这个月」按 `note.md` 时间粒度 |
| 列表带正文 | ✅ | 「列表里把内容也带上」 | `withContent=true` | |
| 列表/详情短链 | ✅ | 「要短链」 | 列表/详情传 `withShortUrl=true` | 用户没要分享不要传 |
| 单条详情 | ✅ 组合 1～2 | 「打开这条」 | 已有 ID：`querySingleNoteDetail`。只有标题：先列表再详情 | 处理中须说明 |
| 只要转写 / 只要总结 | ✅ 组合 1～2 | 「只要转写原文」 | 详情后只展示 `content` 或 `summary` | 不把 summary 冒充原文；`recognizing`/`analyzing` 提示未完成 |
| 主笔记 + 追加段 | ✅ 组合 1～2 | 「把追加的也给我」 | ① 无 ID 先查 ② `GET /note/qryNoteDetailInfoAndAppend` | 不要只读单条详情再编造追加段 |
| 处理进度 | ✅ 组合 1～2 | 「转写好了吗」 | `GET /note/queryNoteStatus` | pending / recognizing / analyzing / completed / failed |
| 等到完成再给内容 | ✅ 组合 2～3 | 「等它处理完再给我」 | ① 无 ID 先查 ② 轮询 status ③ 仅 completed 后再详情 | 失败如实返回，不自动再创建 |

---

## 修改 / 删除 / 下载

| 功能 | 落地 | Skill 执行 | 预期 |
|---|---|---|---|
| 改标题 / 摘要 / 总结 | ✅ 组合 2～3 | ① 无 `noteId`：`queryNoteList` 按标题选定真实 ID（零条停、多条让用户选）② `POST /note/updateNoteInfo`（`noteId` 必填；摘要字段 `abstractContent`）③ 详情读回。没有 ID 禁止调用 | 只改传入字段。覆盖总结建议先确认 |
| 删除笔记 | ✅ 组合 2 | ① 确认是哪条 ② 用户确认后 `GET /note/deleteNote?noteId=` | 未确认不删。失败不能说已删 |
| 下载录音 | ✅ 组合 1～2 | ① 无 ID 先查 ② `GET /note/downloadNoteAudio?noteId=` | 非录音失败。只有 fileId 且不是笔记录音 → `GET /file/getFile/{fileId}` |

---

## 场景与知识卡

| 功能 | 落地 | 用户说法 | Skill 执行 |
|---|---|---|---|
| 内置场景 | ✅ | 「有哪些总结场景」 | `GET /note/queryInnerSceneList` |
| 我的场景 | ✅ | 「我的场景」 | `GET /note/queryMySceneList`；含共享则 `includeSharedFlag=true`。空列表是成功 |
| 知识卡 | ✅ | 「我的知识卡」 | `POST /note/queryKnowledgeCardByPage` |

「用某某场景做成笔记」见创建组合 2 步，不是单步列表。

---

## 笔记集

查询与写入均可做。名称先查 ID。删目录须确认。

| 功能 | 落地 | Skill 执行 |
|---|---|---|
| 我创建的 | ✅ | `POST /note/queryNoteKnowledge`（`qryType=myCreate`） |
| 我收到的 | ✅ | `POST /note/queryNoteKnowledgeEmpower` |
| 打开笔记集 / 目录 | ✅ 组合 2～3 | ① 按名称 list 得 `knowledgeId` ② 点目录再 `queryKnowledgeCatalog` ③ `queryNoteKnowledgeDetail`。不要一上来编 ID |
| 新建笔记集 | ✅ | `POST /note/createNoteKnowledge`（`knowledgeName`） |
| 建目录 | ✅ 组合 2 | ① 查 `knowledgeId` ② `POST /note/addKnowledgeCatalog` |
| 移笔记到目录 / 根层 / 批量 | ✅ 组合 2～4 | ① 查笔记与笔记集/目录 ID ② `POST /note/moveNotesToKnowledge` |
| 删除目录 | ✅ 组合 2～3 | ① 查 `directoryId` ② 确认后 `GET /note/deleteKnowledgeCatalog` |

---

## 问小智（语义检索 / 会话问答）

任何提问都是两步：先 `createXiaozhiSession`，再 `xiaozhiChat`。创建会话也要带同一句 `query`。协议见 [`xiaozhi.md`](xiaozhi.md)。

| 功能 | 落地 | 本 Skill |
|---|---|---|
| 「找/搜/关于某主题」语义问答 | ✅ 组合 2 | ① `createXiaozhiSession` ② `xiaozhiChat`。不要用 `queryNoteList` 冒充 |
| 「在工作笔记集里问」 | ✅ 组合 3 | ① 查 `knowledgeId` ② 会话带该 ID ③ SSE |
| 「只问某某目录」 | ✅ 组合 4 | ① 查笔记集 ② `queryKnowledgeCatalog` 得目录 ③ 会话带 `knowledgeId`+`directoryId` ④ SSE |
| 「就那条纪要，待办有哪些」 | ✅ 组合 2～3 | 有 `noteId`（或先按标题查到）后会话带 `noteId` 再问答 |
| 追问 | ✅ | 已有 `chatId`+`contextId` 时直接 `xiaozhiChat`。`lastChatId` 只用于断线续传 |
| 带参考文档 | ✅ | 问答 `withReferences=true`；SSE 有 `references` 再 `qryXiaozhiReferences` |
| 空问题 | ✅ 失败 | 停：问题不能为空 |
| 未创建会话就问答 | ✅ 失败 | SSE `error` 原文。不要自动补调创建会话 |
| 范围内无内容 | ✅ 失败 | SSE `notData`/`error` 原文，不要编答案 |

写周报、按结构总结 **不是**问小智，走动态模版管线。

---

## 其它

| 功能 | 落地 | Skill 执行 |
|---|---|---|
| 给文字流式总结 | ✅ | 点了场景名则先查真实 `sceneId`，再 `POST /note/createTextNoteSummary` SSE。没点可以不传。不是问小智，也不是某条笔记 summary |
| 动态模版周报/复盘 | ✅ | 归一化 → `GET /know/queryStandardInputOutputByCommand` → 查笔记列表（必要时详情）→ 成文。可跳过：纯增删改、上传、下录音、视频创建、文字 SSE、问小智、以及不依赖多篇笔记成文的操作 |

---

## 跨模块组合

模块内组合按上表。这里不要只执行最后一条。

| 功能 | 落地 | 用户说法 | Skill 顺序 |
|---|---|---|---|
| 会议录音一条龙 | ✅ | 「导入，用会议场景，放到工作笔记集，处理好把纪要给我」 | ① 查 `sceneId` ② 查 `knowledgeId` ③ 做成笔记带场景+归档并等待 ④ 给纪要。中途失败停在对应步 |
| 追加续录 | ✅ | 「刚才那条会又录了 2 分钟，追加上」 | 无 ID 先查 → `appendNoteId` 创建并等待 → 要全文再读详情 |
| 先列后读 | ✅ | 「最近录音里有没有经营分析，打开总结」 | `queryNoteList` `noteType=voice` + `title` → 选定后详情只展示 `summary`。这是标题过滤 |
| 语义查找再打开 | ✅ | 「找找关于支付的，打开最相关那条」 | ① 问小智 ② 用引用里的真实 `noteId` 打开详情。不要把列表说成智能搜索，不要把回答标题当 ID |
| 改名后删除误建 | ✅ | 「标题改对，另一条删掉」 | 两条都先有 ID → update → 读回 → 确认后 delete |
| 未完成再取 | ✅ | 「上次那条还在转，好了叫我」 | 轮询 status → 仅 completed 后详情。失败不自动再创建 |
| 建集、建目录、归档 | ✅ | 「新建工作笔记集，建目录，把这条放进去」 | ① `createNoteKnowledge` ② `addKnowledgeCatalog` ③ `moveNotesToKnowledge` |
| 问完再归档 | ✅ | 「先找支付相关，放进工作笔记集」 | ① 问小智 ② 查笔记集 ③ 用真实 `noteId` 调 `moveNotesToKnowledge` |

以下按做成笔记单步即可：收藏网页、白板照片、按文件/文档/视频入库、已有 `noteId` 时导出音频。

---

## 失败与边界

| 功能 | 落地 | 预期 |
|---|---|---|
| 缺文件 / 类型无法识别 | ✅ | 本地失败，不调创建 |
| 上传失败后再创建 | ✅ | 业务校验错误，不用空 fileId 创建 |
| 场景无效 | ✅ | 创建失败。应在创建前用场景列表对上真实 ID |
| 笔记集无效 / 无法归档 | ⚠️ | 笔记仍可能创建成功。必须拆开说「已创建，但未归档」 |
| 轮询得到 failed / *_failed | ✅ | 展示状态；禁止自动再创建 |
| 笔记不存在/无权限 | ✅ | `resultMsg` 原样 |
| 笔记列表 / 笔记集列表无数据 | ✅ | 成功：没有符合条件的笔记/笔记集 |
| 删除未确认 | ✅ | 先确认 |
| 把组合当成单步（有名称无 ID 就写） | ✅ 判错 | 补齐查询步。查不到则停 |
| 问小智无会话 | ✅ 失败 | SSE `error` 原文；不要自动建会话、不要编答案 |
| 问小智范围内无内容 | ✅ 失败 | SSE `notData`/`error` 原文 |
