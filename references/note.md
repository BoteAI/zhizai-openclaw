# 智在记录 · 笔记

通过开放 API 完成笔记检索、增删改查、上传与下载。不要凭印象猜字段；机器调用以本文件「接口协议」为准。

语义检索走 [`xiaozhi.md`](xiaozhi.md)，不要用本文件的列表冒充。不要调用问小智 URL 配置 `addOrUpdateParamsByCode`。

对外一次「做成笔记」时，内部才允许上传 + 创建 + 轮询，不要对用户呈现「已上传」半成品。

## 统一结果判定

先看 HTTP：`400`/`401`/`406` → 无权限（检查 `ZHIZAI_REC_API_KEY`）。再看 JSON：`resultCode == "0"` 为成功。

```json
{
  "resultCode": "0",
  "resultMsg": "success",
  "resultObject": {},
  "stack": "",
  "errorInfos": null,
  "guidance": null
}
```

对用户：可用 `resultMsg` 短句；禁止展示完整 Key、`stack`、未脱敏 `errorInfos`。限流 ≤2 次/秒。

`ZHIZAI_BASE_URL` = `https://openapi.zzjilu.com/api/v1`。Header：`Authorization: ${ZHIZAI_REC_API_KEY}`（无 Bearer）。
如返回「缺失应用 ID」，下载音频、移笔记再补 `APP-ID`（见 SKILL.md）。

## 动态模版管线（周报 / 复盘 / 按结构总结）

用户明确要按结构成文（写周报、复盘、按某某结构总结）时走本管线。可跳过：纯新建/编辑/删除、上传、下录音、文字总结 SSE、问小智、以及不依赖多篇笔记成文的操作。

「找、搜、关于某主题」的**语义问答**走 [`xiaozhi.md`](xiaozhi.md)。不要用本管线或 `queryNoteList` 冒充语义搜索。

必须按序：

1. **归一化**：主题词、时间词、用户自带模版。
2. **查模版**：`GET /know/queryStandardInputOutputByCommand?command=`（URL 编码）。先关键词；`output` 空再用完整原句；两次仍空则语义兜底。
3. **查笔记**：`POST /note/queryNoteList`（时间范围、`pageSize` 默认 100 翻页）；需要正文再 `GET /note/querySingleNoteDetail`。
4. **成文**：用户模版 > 接口 `output` > 语义兜底（概览→发现→建议）。无相关笔记则柔和说明，禁止编造。

## 时间粒度与类型

列表按用户时间词填 `startTime` / `endTime`：

| 表述 | startTime | endTime |
|---|---|---|
| 本周 | 本周一 00:00:00 | 本周日 23:59:59 |
| 本月 | 本月 1 日 00:00:00 | 本月最后一天 23:59:59 |
| 本季度 | 本季首月 1 日 00:00:00 | 本季末月最后一天 23:59:59 |
| 本年 | 1 月 1 日 00:00:00 | 12 月 31 日 23:59:59 |

不得跨入未来。「上周/上月」等减一个周期。

### note_type 中文映射

| 值 | 中文 |
|---|---|
| text | 文本 |
| voice | 录音 |
| document | 文档 |
| link | 链接 |
| image | 图片 |
| video | 视频 |
| knowCard | 知识卡片 |

### noteState（仅进度，非正文）

`completed` 已完成 / `pending` 处理中 / `recognizing` 转写中 / `analyzing` 总结中 / `failed` 失败 / `recognizing_failed` 转写失败 / `analyzing_failed` 总结失败。

## 意图路由

| 用户意图（场景说法） | 接口入口 |
|---|---|
| 周报/复盘/按结构成文（不是问小智） | `GET /know/queryStandardInputOutputByCommand` |
| 最近/类型/标题/时间列表（不是语义搜索） | `POST /note/queryNoteList` |
| 打开详情；只要原文/总结则只展示 `content`/`summary` | `GET /note/querySingleNoteDetail` |
| 主笔记 + 追加段 | `GET /note/qryNoteDetailInfoAndAppend` |
| 进度 / 等到完成 | `GET /note/queryNoteStatus`（等待=轮询至 `completed`/`failed`/`*_failed`） |
| 删除（先确认） | `GET /note/deleteNote` |
| 改标题/摘要/总结 | 先有真实 `noteId`，再 `POST /note/updateNoteInfo`。无 ID：先 `queryNoteList` |
| 只上传、不创建笔记 | `POST /file/uploadSingleFile` |
| 按 fileId 取回文件 | `GET /file/getFile/{fileId}` |
| 做成文字/链接/录音/图片/文档笔记 | `POST /note/createNote`（需文件时内部先上传） |
| 给一段文字流式总结 | `POST /note/createTextNoteSummary`（点了场景名才查 `sceneId`） |
| 下载笔记录音 | `GET /note/downloadNoteAudio` |
| 语义问答 | 见 [`xiaozhi.md`](xiaozhi.md)，不要用本文件 |

无 `noteId` 时禁止详情/改删/下载/等待。先 `queryNoteList` 按标题匹配，零条停、多条让用户选。**改标题/摘要/总结必须先拿到真实 `noteId` 再调 `updateNoteInfo`**，没有 ID 禁止调用。用户没要分享时不要主动短链；需要时才传 `withShortUrl=true`。不把 `summary` 冒充转写原文。

`createNote` 录音可带 `voiceContent.knowledgeId` / `directoryId`：用户说「放到某某笔记集」时先解析真实 ID 再写入。无效 `knowledgeId`：笔记可能已创建，必须写清「已创建但未归档」。不传目录或 `-1` 表示笔记集根层。

`appendNoteId` 对应「追加到已有会」。必须先有真实 `noteId`。

按 fileId 取回文件：`GET /file/getFile/{fileId}`。路径参数 `fileId` 当字符串。成功是二进制或重定向到文件服务器（curl 要 `--location`）。HTTP 404 表示文件不存在。用户要笔记录音原文件时用 `downloadNoteAudio`。

详情：`resultCode=0` 但 `resultObject.id` 为空（或对象无标题）→ 笔记不存在，不要说已打开。

下载录音 / 按 fileId 取回：成功才是二进制流，或跟随重定向后再落盘。若返回 JSON，如实失败，不要假装已保存到本地。`downloadNoteAudio` 若报「缺失应用 ID」，补 Header `APP-ID`（上传回包 `appId`）。`GET /file/getFile/{fileId}`：404=文件不存在；401 空 body=Key 未勾选该接口。

`updateNoteInfo` / 部分写接口若 `401` 且文案含「请关联API」（或空 body）：当前 Key 未授权该接口，引导去开发者后台勾选，不要改用错误接口冒充已改标题。

## 新建与文件依赖

| 场景 | noteType | 须先上传 |
|---|---|---|
| 文本 | text | 否 |
| 链接 | link | 否 |
| 文档 | document | 是 → `documentContent.fileId` |
| 图片 | image | 是 → `imageContent.fileIds[].fileId` |
| 录音 | voice | 是 → `voiceContent.voiceFileId` |

本地视频不能做成笔记：停并说明。用户只要「上传」则只 `uploadSingleFile`。禁止当成录音。

对外一次「做成笔记」：内部才 `uploadSingleFile` → `createNote` → 异步类型默认轮询 `queryNoteStatus` 至终态 → 仅 `completed` 后再读详情。用户说不用等则不轮询。路径不存在或扩展名不支持时本地失败，不调创建接口。

录音/图片/文档默认等待；文字与链接通常无需等待。成功最低标准：非空 `noteId`。只有 `completed` 才能宣称转写/总结已完成。`failed` / `recognizing_failed` / `analyzing_failed` 禁止自动再创建。

## 结果呈现

- 列表：`id`、`title`、中文类型、`create_time`；有 `summary` 用总结否则 `abstract`。
- 保存成功：真实 ID、标题、`note_state`；处理中勿伪造成文完成。
- 进度接口只谈系统阶段，内容问题必须用列表/详情。

## 接口协议

### POST `/note/queryNoteList`  查询笔记列表

**接口说明**：获取用户笔记列表，支持模糊查询，支持分页，支持按是否返回详情查询  

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| title | string | 否 | 标题（模糊匹配） |
| abstractContent | string | 否 | 摘要（模糊匹配） |
| summary | string | 否 | 总结（模糊匹配） |
| content | string | 否 | 内容（模糊匹配） |
| noteType | string | 否 | 笔记类型（voice/text/image/document/link） |
| noteCategory | integer | 否 | 笔记分类 |
| startTime | string | 否 | 开始时间 |
| endTime | string | 否 | 结束时间 |
| pageNum | integer | 否 | 当前页码（默认1） |
| pageSize | integer | 否 | 每页条数（默认10） |
| withContent | string | 否 | 是否返回内容（true/false） |
| withShortUrl | string | 否 | `"true"` 时列表带短链。用户没要分享不要传 |

#### 请求示例

```bash
curl --request POST \
  --url https://openapi.zzjilu.com/api/v1/note/queryNoteList \
  --header 'Authorization: your api-key' \
  --header 'content-type: application/json' \
  --data '{
	"title": "语音识别",
	"abstractContent": "",
	"summary": "",
	"content": "",
	"noteType": "",
	"noteCategory": null,
	"startTime": "",
	"endTime": "",
	"pageNum": 1,
	"pageSize": 20,
	"withContent": ""
}'
```

#### 响应参数

| 参数名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| resultCode | string | 是 | 结果码，0表示成功 |
| resultMsg | string | 是 | 结果信息，成功时为success |
| resultObject | object | 是 | 返回数据对象 |
| resultObject.startRow | string | 否 | 起始行 |
| resultObject.pageNum | integer | 是 | 当前页码 |
| resultObject.pageSize | integer | 是 | 每页条数 |
| resultObject.total | string | 是 | 总记录数 |
| resultObject.pages | integer | 是 | 总页数 |
| resultObject.size | integer | 是 | 当前页实际记录数 |
| resultObject.hasNextPage | boolean | 是 | 是否TF有下一页 |
| resultObject.hasPreviousPage | boolean | 是 | 是否TF有上一页 |
| resultObject.isFirstPage | boolean | 是 | 是否TFT第一页 |
| resultObject.isLastPage | boolean | 是 | 是否TFT最后一页 |
| resultObject.prePage | integer | 否 | 上一页页码 |
| resultObject.nextPage | integer | 否 | 下一页页码 |
| resultObject.navigateFirstPage | integer | 否 | 导航第一页 |
| resultObject.navigateLastPage | integer | 否 | 导航最后一页 |
| resultObject.navigatepageNums | array | 否 | 导航页码数组 |
| resultObject.navigatePages | integer | 是 | 导航页码数量 |
| resultObject.list | array | 是 | 数据列表 |
| resultObject.list[].id | string | 是 | 记录ID |
| resultObject.list[].title | string | 是 | 标题 |
| resultObject.list[].summary | string | 是 | 总结 |
| resultObject.list[].abstract | string | 是 | 摘要 |
| resultObject.list[].content | object | 否 | 内容（录音笔记为转写数组，文本/文档类型为字符串，可为空） |
| resultObject.list[].status | string | 是 | 状态码 |
| resultObject.list[].note_type | string | 是 | 笔记类型 |
| resultObject.list[].note_state | string | 是 | 笔记状态 |
| resultObject.list[].create_time | string | 是 | 创建时间 |
| resultObject.list[].creator_id | string | 是 | 创建人ID |
| resultObject.list[].scene_name | string | 是 | 场景名称 |
| resultObject.list[].scene_id | string | 是 | 场景ID |
| resultObject.list[].source_note_id | string | 否 | 来源笔记ID |
| resultObject.list[].note_category | integer | 否 | 笔记分类 |
| resultObject.list[].device_sn | string | 否 | 录音卡SN码（仅录音笔记返回） |
| resultObject.list[].latitude | string | 否 | 录音地理位置纬度（仅录音笔记返回） |
| resultObject.list[].longitude | string | 否 | 录音地理位置经度（仅录音笔记返回） |
| resultObject.list[].rec_end_time | string | 否 | 录制结束时间（仅录音笔记返回） |
| resultObject.list[].account_num | string | 否 | 创建者账号/手机号（仅录音笔记返回） |
| stack | string | 否 | 异常堆栈信息 |
| errorInfos | array | 否 | 错误信息列表 |
| guidance | string | 否 | 引导信息 |

#### 响应示例

```json
{
  "resultCode": "0",
  "resultMsg": "success",
  "resultObject": {
    "startRow": "0",
    "navigatepageNums": null,
    "prePage": 0,
    "hasNextPage": false,
    "nextPage": 0,
    "pageSize": 20,
    "endRow": "0",
    "list": [
      {
        "id": "31023",
        "title": "语音识别技术进展",
        "summary": "![ai:1351071340606681088](https://lingxi.iwhalecloud.com/LCDP-RECORD/lcdp-app/server/app/file/file/id/1351071340606681088?appId=1277144354029191168&width=1736&height=1920)\n\n## 模块升级进展\n- **语音转文字模块升级**：多模型切换策略\n- **说话人分离模块效果提升**：说话人日志错误率从37%降到6%\n- **声纹向量模块升级**：维度从192维升到256维",
        "content": [],
        "status": "00A",
        "abstract": "讨论语音识别模块升级、测试反馈及数据收集方案，包括方言处理和英文识别优化",
        "note_type": "voice",
        "create_time": "2026-03-17 13:45:18",
        "creator_id": "8912493637529600",
        "note_state": "completed",
        "scene_name": "智能场景",
        "source_note_id": null,
        "scene_id": "0",
        "note_category": null,
        "device_sn": "1234567890",
        "latitude": "32.060255",
        "longitude": "118.796877",
        "rec_end_time": "2026-03-17 13:45:18",
        "account_num": "13900001111"
      }
    ],
    "pageNum": 1,
    "navigatePages": 0,
    "total": "1",
    "navigateFirstPage": 0,
    "pages": 0,
    "size": 1,
    "isLastPage": false,
    "hasPreviousPage": false,
    "navigateLastPage": 0,
    "isFirstPage": false
  },
  "stack": "",
  "errorInfos": null,
  "guidance": null
}
```

### GET `/note/querySingleNoteDetail`  查询笔记

**接口说明**：查询单条笔记信息，支持按笔记ID查询笔记详情  

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| noteId | string | 是 | 笔记ID |
| withShortUrl | string | 否 | `"true"` 才返回 `short_url` |

#### 请求示例

```bash
curl --request GET \
  --url 'https://openapi.zzjilu.com/api/v1/note/querySingleNoteDetail?noteId=30480' \
  --header 'Authorization: your api-key'
```

#### 响应参数

| 参数名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| resultCode | string | 是 | 结果码，0表示成功 |
| resultMsg | string | 是 | 结果信息，成功时为success |
| resultObject | object | 是 | 返回数据对象 |
| resultObject.id | string | 是 | 笔记ID |
| resultObject.title | string | 是 | 标题 |
| resultObject.summary | string | 是 | 总结内容 |
| resultObject.abstract | string | 是 | 摘要 |
| resultObject.content | object | 是 | 详细内容（录音笔记为转写数组，文本/文档类型为字符串） |
| resultObject.status | string | 是 | 状态码 |
| resultObject.note_type | string | 是 | 笔记类型 |
| resultObject.note_state | string | 是 | 笔记状态 |
| resultObject.create_time | string | 是 | 创建时间 |
| resultObject.creator_id | string | 是 | 创建人ID |
| resultObject.scene_name | string | 是 | 场景名称 |
| resultObject.scene_id | string | 是 | 场景ID |
| resultObject.source_note_id | string | 否 | 来源笔记ID |
| resultObject.note_category | integer | 否 | 笔记分类 |
| resultObject.device_sn | string | 否 | 录音卡SN码（仅录音笔记返回） |
| resultObject.latitude | string | 否 | 录音地理位置纬度（仅录音笔记返回） |
| resultObject.longitude | string | 否 | 录音地理位置经度（仅录音笔记返回） |
| resultObject.rec_end_time | string | 否 | 录制结束时间（仅录音笔记返回） |
| resultObject.account_num | string | 否 | 创建者账号/手机号（仅录音笔记返回） |
| stack | string | 否 | 异常堆栈信息 |
| errorInfos | array | 否 | 错误信息列表 |
| guidance | string | 否 | 引导信息 |

#### 响应示例

```json
{
  "resultCode": "0",
  "resultMsg": "success",
  "resultObject": {
    "id": "30480",
    "title": "通话测试确认",
    "summary": "## 会议目标\n- 进行通话设备测试。\n\n## 关键信息\n- 通话开始阶段，陈楚旭多次重复“喂”和“你好”，并进行“测试测试”的呼叫。",
    "content": [
      {
        "recording_id": "14853",
        "transcript": [
          {
            "raw_text": "嗯，喂喂喂喂喂喂，你好，你好，你好喂喂喂，测试测试",
            "start": 280,
            "end": 7245,
            "tn_text": "嗯，",
            "text": "嗯，喂喂喂喂喂喂，你好，你好，你好喂喂喂，测试测试。",
            "spk": "陈楚旭"
          }
        ],
        "duration": "7",
        "start_time": null,
        "create_time": "2026-01-26 10:52:40"
      }
    ],
    "status": "00A",
    "abstract": "通话开始前的设备测试和连接确认过程",
    "note_type": "voice",
    "create_time": "2026-01-26 10:52:40",
    "creator_id": "8912493637529600",
    "note_state": "completed",
    "scene_name": "智能场景",
    "source_note_id": null,
    "scene_id": "0",
    "note_category": null,
    "device_sn": "0012345678",
    "latitude": null,
    "longitude": null,
    "rec_end_time": "2026-01-26 10:52:47",
    "account_num": "13900001111"
  },
  "stack": "",
  "errorInfos": null,
  "guidance": null
}
```

### GET `/note/deleteNote`  删除笔记

**接口说明**：删除笔记，支持按笔记ID删除笔记  

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| noteId | string | 是 | 笔记ID |

#### 请求示例

```bash
curl --request GET \
  --url 'https://openapi.zzjilu.com/api/v1/note/deleteNote?noteId=31559' \
  --header 'Authorization: your api-key'
```

#### 响应参数

| 参数名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| resultCode | string | 是 | 结果码 |
| resultMsg | string | 是 | 结果信息 |
| resultObject | null | 是 | 返回数据对象（为null） |
| stack | string | 是 | 异常堆栈信息 |
| errorInfos | null | 是 | 错误信息列表（为null） |
| guidance | null | 是 | 引导信息（为null） |

#### 响应示例

```json
{
  "resultCode": "0",
  "resultMsg": "success",
  "resultObject": null,
  "stack": "",
  "errorInfos": null,
  "guidance": null
}
```

### GET `/note/queryNoteStatus`  查询笔记状态

**接口说明**：查询笔记处理进度，completed:已完成；pending:处理中；recognizing:转写中；analyzing:总结中；failed:失败  

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| noteId | string | 是 | 笔记ID |

#### 请求示例

```bash
curl --request GET \
  --url 'https://openapi.zzjilu.com/api/v1/note/queryNoteStatus?noteId=31560' \
  --header 'Authorization: your api-key'
```

#### 响应参数

| 参数名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| resultCode | string | 是 | 结果码，0表示成功 |
| resultMsg | string | 是 | 结果信息，成功时为success |
| resultObject | object | 是 | 返回数据对象 |
| resultObject.noteState | string | 是 | 笔记状态（completed：已完成） |
| stack | string | 是 | 异常堆栈信息 |
| errorInfos | null | 是 | 错误信息列表 |
| guidance | null | 是 | 引导信息 |

#### 响应示例

```json
{
  "resultCode": "0",
  "resultMsg": "success",
  "resultObject": {
    "noteState": "completed"
  },
  "stack": "",
  "errorInfos": null,
  "guidance": null
}
```

### POST `/note/updateNoteInfo`  修改笔记

**接口说明**：修改笔记，部分修改笔记标题、短摘要或 AI 录音总结；未传或空白的字段保持不变。**`noteId` 必填**。用户只说标题或「这条」时，必须先 `queryNoteList` 拿到真实 ID，再调本接口；没有 `noteId` 禁止调用。改完再 `querySingleNoteDetail` 读回。 

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| noteId | string | 是 | 笔记ID |
| title | string | 否 | 笔记标题（未传或空白保持不变） |
| abstractContent | string | 否 | 笔记摘要（未传或空白保持不变） |
| summary | string | 否 | 笔记总结（未传或空白保持不变） |

#### 请求示例

```bash
curl --request POST \
  --url https://openapi.zzjilu.com/api/v1/note/updateNoteInfo \
  --header 'Authorization: your api-key' \
  --header 'content-type: application/json' \
  --data '{
	"noteId": "31560",
	"title": "测试1",
	"abstractContent": "",
	"summary": ""
}'
```

#### 响应参数

| 参数名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| resultCode | string | 是 | 结果码 |
| resultMsg | string | 是 | 结果信息 |
| resultObject | null | 是 | 返回数据对象（为null） |
| stack | string | 是 | 异常堆栈信息 |
| errorInfos | null | 是 | 错误信息列表（为null） |
| guidance | null | 是 | 引导信息（为null） |

#### 响应示例

```json
{
  "resultCode": "0",
  "resultMsg": "success",
  "resultObject": null,
  "stack": "",
  "errorInfos": null,
  "guidance": null
}
```

### POST `/note/createNote`  创建笔记

**接口说明**：创建新笔记，支持创建录音、文档、图片、链接、文字等类型的笔记，支持按指定场景总结  

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| noteType | string | 是 | 笔记类型（voice/text/image/document/link） |
| sceneId | Long | 否 | 场景ID（按指定场景总结） |
| voiceContent | object | 否 | 录音笔记内容（noteType=voice时传入） |
| voiceContent.text | string | 否 | 随手记（语音转文字内容） |
| voiceContent.voiceFileId | string | 否 | 音频文件ID |
| voiceContent.title | string | 否 | 自定义标题（也认错拼 `titile`） |
| voiceContent.recStartTime | string | 否 | 录制开始时间 |
| voiceContent.recEndTime | string | 否 | 录制结束时间（yyyy-MM-dd HH:mm:ss） |
| voiceContent.duration | string | 否 | 录音时长，单位秒 |
| voiceContent.imageFileIds | array | 否 | 随手拍图片文件ID列表 |
| voiceContent.appendNoteId | string | 否 | 追加笔记ID |
| voiceContent.deviceSn | string | 否 | 录音卡SN码 |
| voiceContent.latitude | string | 否 | 录音地理位置纬度 |
| voiceContent.longitude | string | 否 | 录音地理位置经度 |
| voiceContent.recordingSource | string | 否 | `realtime` / `phoneInternal` / `offlineImport` / `recordingCard`。未指定时传 `offlineImport` |
| voiceContent.knowledgeId | string | 否 | 总结完成后归档到该笔记集。无效时笔记仍可能创建成功 |
| voiceContent.directoryId | string | 否 | 与 `knowledgeId` 组合；不传或 `-1` 表示笔记集根层 |
| textContent | object | 否 | 文字笔记内容（noteType=text时传入） |
| textContent.title | string | 否 | 笔记标题 |
| textContent.content | string | 否 | 文字内容 |
| imageContent | object | 否 | 图片笔记内容（noteType=image时传入） |
| imageContent.fileIds | array | 否 | 图片文件列表 |
| imageContent.fileIds[].fileId | string | 否 | 图片文件ID |
| imageContent.fileIds[].remark | string | 否 | 图片备注 |
| documentContent | object | 否 | 文档笔记内容（noteType=document时传入） |
| documentContent.fileId | string | 否 | 文件ID |
| documentContent.fileName | string | 否 | 文件名称 |
| documentContent.title | string | 否 | 笔记标题，优先于文件名 |
| linkContent | object | 否 | 链接笔记内容（noteType=link时传入） |
| linkContent.url | string | 否 | 链接地址 |

#### 请求示例

```bash
curl --request POST \
  --url https://openapi.zzjilu.com/api/v1/note/createNote \
  --header 'Authorization: your api-key' \
  --header 'content-type: application/json' \
  --data '{
  "noteType" : "document",
  "documentContent" : {
    "fileId" : "1357179569765883904",
    "fileName" : "开店选址手册.docx"
  }
}'
```

#### 响应参数

| 参数名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| resultCode | string | 是 | 结果码，0表示成功 |
| resultMsg | string | 是 | 结果信息，成功时为success |
| resultObject | object | 是 | 返回数据对象 |
| resultObject.id | string | 是 | 笔记ID |
| resultObject.title | string | 是 | 标题 |
| resultObject.summary | string | 是 | 总结内容（处理中时为提示文案） |
| resultObject.abstract | string | 是 | 摘要（处理中时为提示文案） |
| resultObject.content | object | 否 | 详细内容（处理中时为null；录音笔记为转写数组，文本/文档类型为字符串） |
| resultObject.status | string | 是 | 状态码 |
| resultObject.note_type | string | 是 | 笔记类型 |
| resultObject.note_state | string | 是 | 笔记状态（pending:处理中，completed:已完成） |
| resultObject.create_time | string | 是 | 创建时间 |
| resultObject.creator_id | string | 是 | 创建人ID |
| resultObject.scene_name | string | 否 | 场景名称（pending时为null） |
| resultObject.scene_id | string | 否 | 场景ID（pending时为null） |
| resultObject.source_note_id | string | 否 | 来源笔记ID |
| resultObject.note_category | integer | 否 | 笔记分类 |
| resultObject.device_sn | string | 否 | 录音卡SN码（仅录音笔记返回） |
| resultObject.latitude | string | 否 | 录音地理位置纬度（仅录音笔记返回） |
| resultObject.longitude | string | 否 | 录音地理位置经度（仅录音笔记返回） |
| resultObject.rec_end_time | string | 否 | 录制结束时间（仅录音笔记返回） |
| resultObject.account_num | string | 否 | 创建者账号/手机号（仅录音笔记返回） |
| stack | string | 否 | 异常堆栈信息 |
| errorInfos | array | 否 | 错误信息列表 |
| guidance | string | 否 | 引导信息 |

#### 响应示例

```json
{
  "resultCode": "0",
  "resultMsg": "success",
  "resultObject": {
    "id": "31561",
    "title": "开店选址手册.docx",
    "summary": "等待约 1 分钟！整理下桌面的便利贴，把杂乱归位，记录就新鲜出炉咯～",
    "content": null,
    "status": "00A",
    "abstract": "等待约 1 分钟！整理下桌面的便利贴，把杂乱归位，记录就新鲜出炉咯～",
    "note_type": "document",
    "create_time": "2026-04-08 17:17:48",
    "creator_id": "8912493637529600",
    "note_state": "pending",
    "scene_name": null,
    "source_note_id": null,
    "scene_id": null,
    "note_category": null,
    "device_sn": null,
    "latitude": null,
    "longitude": null,
    "rec_end_time": null,
    "account_num": null
  },
  "stack": "",
  "errorInfos": null,
  "guidance": null
}
```

### POST `/note/createTextNoteSummary`  生成文字笔记总结

**接口说明**：生成文字笔记总结  

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| content | string | 是 | 笔记内容 |
| sceneId | string | 否 | 场景ID。用户点了场景名必须先查到真实 ID；没点可以不传 |

#### 请求示例

```bash
curl --request POST \
  --url 'https://openapi.zzjilu.com/api/v1/note/createTextNoteSummary' \
  --header 'Authorization: your api-key' \
  --header 'content-type: application/json' \
  --data '{
  "content" : "笔记内容",
  "sceneId" : "场景ID"
}'
```

#### 响应参数

| 参数名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| Content-Type | header | 是 | text/event-stream，SSE流式响应 |
| data | string | 是 | SSE事件流数据，每个data事件为AI总结的增量文本片段，逐块推送直至流结束 |

#### 响应示例

```json
data: ## 会议目标
data: - 进行通话设备测试。
data: （SSE流式响应，每个data事件为AI总结增量文本片段，直至流结束）
```

### POST `/file/uploadSingleFile`  文件上传

**接口说明**：文件上传，仅支持单个文件上传，可以通过设置compressFile控制是否压缩存储  

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| compressFile | boolean | 否 | 是否压缩存储 |
| file | file | 是 | 上传的文件（支持图片、文档等） |

#### 请求示例

```bash
curl --request POST \
  --url https://openapi.zzjilu.com/api/v1/file/uploadSingleFile \
  --header 'Authorization: your api-key' \
  --header 'content-type: multipart/form-data' \
  --form file=@/Users/xxx/Desktop/20260408_085359_8922_0.m4a
```

#### 响应参数

| 参数名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| resultCode | string | 是 | 结果码，0表示成功 |
| resultMsg | string | 是 | 结果信息，成功时为success |
| resultObject | object | 是 | 返回数据对象 |
| resultObject.fileId | string | 是 | 文件ID |
| resultObject.storeType | string | 是 | 存储类型 |
| resultObject.filePathInServer | string | 是 | 服务器文件路径 |
| resultObject.fileName | string | 是 | 文件名称 |
| resultObject.fileDesc | string | 否 | 文件描述 |
| resultObject.createDate | string | 是 | 创建时间 |
| resultObject.statusCd | string | 是 | 状态码 |
| resultObject.statusDate | string | 是 | 状态时间 |
| resultObject.appId | string | 是 | 应用ID |
| resultObject.fileSize | string | 否 | 文件大小 |
| resultObject.fileType | string | 否 | 文件类型 |
| resultObject.isPicture | string | 否 | TF为图片 |
| stack | string | 是 | 异常堆栈信息 |
| errorInfos | null | 是 | 错误信息列表 |
| guidance | null | 是 | 引导信息 |

#### 响应示例

```json
{
  "resultCode": "0",
  "resultMsg": "success",
  "resultObject": {
    "fileId": "1359112903776927744",
    "storeType": "MINIO",
    "filePathInServer": "lcdp-g/2026/04/08/a7cfe905-108f-4e38-b495-320ae3545f25.m4a",
    "fileName": "20260408_085359_8922_0.m4a",
    "fileDesc": null,
    "createDate": "2026-04-08 18:29:28",
    "statusCd": "00A",
    "statusDate": "2026-04-08 18:29:28",
    "appId": "1358762423120310272",
    "fileSize": null,
    "fileType": null,
    "isPicture": null
  },
  "stack": "",
  "errorInfos": null,
  "guidance": null
}
```

### GET `/note/downloadNoteAudio`  下载录音笔记音频

**接口说明**：根据笔记ID下载当前用户录音笔记的音频文件；单个音频直接返回音频文件，多个音频打包为ZIP压缩包下载  

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| noteId | Long | 是 | 笔记ID |

#### 请求示例

```bash
curl --request GET \
  --url 'https://openapi.zzjilu.com/api/v1/note/downloadNoteAudio?noteId=30480' \
  --header 'Authorization: your api-key' \
  --output 'note-audio.zip'
```

#### 响应参数

| 参数名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| Content-Type | header | 是 | 单个音频返回音频文件MIME类型（如audio/mpeg）；多个音频打包返回application/octet-stream |
| Content-Disposition | header | 是 | 单个音频为inline;filename=笔记标题.扩展名；多个音频为attachment;filename=笔记标题.zip |
| responseBody | binary | 是 | 二进制文件流，单个音频为音频文件，多个音频为ZIP压缩包 |
| HTTP 404 | error | 否 | 笔记不存在或录音文件不存在 |
| HTTP 400 | error | 否 | 当前笔记不是录音笔记 |

#### 响应示例

```json
{
  "description": "成功时返回二进制文件流（单个音频文件或ZIP压缩包），非JSON格式",
  "successResponse": {
    "status": 200,
    "headers": {
      "Content-Type": "application/octet-stream",
      "Content-Disposition": "attachment; filename*=UTF-8''通话测试确认.zip"
    },
    "body": "<binary file stream>"
  },
  "errorResponses": [
    {
      "status": 404,
      "message": "笔记不存在"
    },
    {
      "status": 400,
      "message": "当前笔记不是录音笔记"
    },
    {
      "status": 404,
      "message": "录音文件不存在"
    },
    {
      "status": 404,
      "message": "录音文件不存在: <fileId>"
    }
  ]
}
```

### GET `/file/getFile/{fileId}`  按文件 ID 下载

**接口说明**：按文件 ID 下载。成功时返回**二进制文件流**，或 **302/301 重定向到文件服务器**，不是统一 JSON。用户说的是「这条会的录音」时走 `downloadNoteAudio`，不要走本接口。没有 `fileId` 禁止调用。

#### 请求参数

| 参数名 | 类型 | 必填 | 位置 | 说明 |
| --- | --- | --- | --- | --- |
| fileId | string | 是 | 路径 | 文件 ID。协议类型是 Long，**当字符串传递**，禁止 JS 数字 |

Header：`Authorization: ${ZHIZAI_REC_API_KEY}`（无 Bearer）。

#### 请求示例

```bash
curl --request GET \
  --url "${ZHIZAI_BASE_URL}/file/getFile/${fileId}" \
  --header "Authorization: ${ZHIZAI_REC_API_KEY}" \
  --location \
  --output meeting.mp3
```

`--location`：成功可能是重定向，必须跟随跳转到文件服务器再落盘。

#### 响应

| 参数名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| Content-Type | header | 是 | 文件 MIME 类型；也可能是重定向响应 |
| responseBody | binary | 是 | 二进制文件流 |
| HTTP 404 | error | 否 | 文件不存在 |

成功：**HTTP 200 二进制**，或 **3xx 后落到文件流**。按 `Content-Type` / `Content-Disposition` 决定扩展名；没有文件名时用用户指定路径或 `downloaded.bin`。

失败：

- HTTP 404：文件不存在，停并说明。
- HTTP 401 且 body 为空：当前 Key 未勾选本接口，引导开发者后台勾选；不要改生产或假装已保存。
- `Content-Type` 为 JSON：读 `resultMsg`/`message`，如实失败，**不要**假装已保存到本地。

### GET `/note/qryNoteDetailInfoAndAppend`  主笔记 + 追加段

Query：`noteId`。

`resultObject.queryMainNoteInfo` 为主笔记；`queryRecordingNote` 等为追加段列表。用户说「把追加的也给我」时走本接口，不要只读单条详情再编造追加段。

### GET `/know/queryStandardInputOutputByCommand`  按指令查询标准输入输出模板

**接口说明**：按指令查询标准输入输出模板，支持控制问小智指定大模型的输入输出格式。用于周报/复盘/按结构总结，**不能**拿来当问小智提问。

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| command | string | 是 | 指令（URL 编码）。先传关键词，`output` 空再用完整原句 |

#### 请求示例

```bash
curl --request GET \
  --url 'https://openapi.zzjilu.com/api/v1/know/queryStandardInputOutputByCommand?command=生成周报' \
  --header 'Authorization: your api-key'
```

#### 响应参数

| 参数名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| resultCode | string | 是 | 结果码，0表示成功 |
| resultMsg | string | 是 | 结果信息 |
| resultObject | object | 是 | 返回数据对象 |
| resultObject.input | string | 是 | 查询输入提示词/检索条件描述 |
| resultObject.output | string | 是 | 成文结构/输出模版 |

`output` 为空时用完整原句再查一次；两次仍空则按「概览 → 发现 → 建议」兜底。成文必须填真实笔记，禁止编造。

