# 智在记录 · 问小智

语义检索与会话问答。任何提问都是两步：**先创建会话，再流式问答**。创建会话也要带同一句 `query`。不要在问答接口里自动建会话。

不要用 `queryNoteList.title` 冒充语义搜索。写周报、按结构成文走 `note.md` 动态模版管线，不是本模块。

## 统一结果判定

先看 HTTP：`400`/`401`/`406` → 无权限（检查 `ZHIZAI_REC_API_KEY`）。JSON 接口再看 `resultCode == "0"`。SSE 看事件名，不要按 `resultCode` 解析流。

对用户：可用 `resultMsg` 短句；禁止展示完整 Key、`stack`、未脱敏 `errorInfos`。限流 ≤2 次/秒。

`ZHIZAI_BASE_URL` = `https://openapi.zzjilu.com/api/v1`。Header：`Authorization: ${ZHIZAI_REC_API_KEY}`（无 Bearer）。

## 范围优先级

服务端按传入 ID 推断，可省略 `chatType`：

1. 有目录 ID → `knowledgeCatalog`（必须同时带所属 `knowledgeId`）
2. 有笔记集 ID → `knowledge`
3. 有笔记 ID → `note`
4. 都没有 → 按个人全部笔记检索（内部 `identify`）

创建与问答必须同一套范围 ID。换主题丢掉 `chatId` / `contextId`，重新创建会话。

追问：已有 `chatId` + `contextId` 时直接调问答，不要再创建会话。`lastChatId` **只用于 SSE 断线续传**，不是追问。

用户说了笔记集/目录/笔记**名称**：先按 `SKILL.md` 名称→ID 查到真实 ID，再进本模块。禁止把名称当 ID。

## 意图路由

| 用户意图 | 接口 |
|---|---|
| 提问（含「找找关于…」） | ① `POST /note/createXiaozhiSession` ② `POST /note/xiaozhiChat` |
| 只要开会话、先别问 | 只 `createXiaozhiSession`（仍须非空 `query` 作标题） |
| 追问 | 仅 `xiaozhiChat`，带回已有 `chatId`+`contextId` |
| 带参考文档 | 问答加 `withReferences=true`；SSE `references` 后再 `qryXiaozhiReferences` |
| 流结束 | `GET /note/clearXiaozhiCache` |

## 使用注意

- `query` 为空则创建会话失败。用户只说「问小智」没有问题：停，不要空传。
- 范围内没有可用笔记会在 SSE 报 `notData` / `error`，用原文，不要编答案。
- 缺 `chatId`/`sessionId` 或 `contextId`：SSE `error`（请先创建会话 / 上下文不能为空）。不要自动补调创建会话。
- 流成功结束后清缓存。有引用则先查引用再清。
- 打开「最相关那条」：先完成问答，用引用里的真实 `noteId` 再调详情；不要把回答标题当 `noteId`。

## 接口协议

### POST `/note/createXiaozhiSession`  创建会话

服务端固定 `stream=false`。

| 字段 | 必填 | 说明 |
|---|---|---|
| query | 是 | 问题，同时作会话标题。空则失败 |
| knowledgeId / knowledgeIdList | 否 | 限定笔记集 |
| noteId / noteIdList | 否 | 限定笔记 |
| directoryId / directoryIdList | 否 | 也认 `catalogId` / `knowledgeCatalogIdList`。根 `-1` 会被忽略 |
| chatType | 否 | 可不传，按 ID 推断 |
| agentCode / botId / sceneId / skillId | 否 | 无智能体不要传 |

个人全部笔记：

```json
{ "query": "找找关于支付的笔记" }
```

限定笔记集（不要带 `noteIdList`、不要带目录）：

```json
{
  "query": "渠道下沉怎么安排的",
  "knowledgeId": "1419241827901288448"
}
```

限定目录（必须带所属笔记集）：

```json
{
  "query": "待办有哪些",
  "knowledgeId": "1419241827901288448",
  "directoryId": "1419000000000000001"
}
```

限定笔记：

```json
{
  "query": "待办有哪些",
  "noteId": "1419261980156293120"
}
```

```bash
curl -X POST "${ZHIZAI_BASE_URL}/note/createXiaozhiSession" \
  -H "Authorization: ${ZHIZAI_REC_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"query":"找找关于支付的笔记"}'
```

`resultObject`：

| 字段 | 说明 |
|---|---|
| sessionId | 会话 ID |
| chatId | 与 `sessionId` 相同（JSON 别名） |
| contextId | 对话上下文，问答必带回 |
| sessionTitle / chatTitle | 标题 |
| prologue | 开场白，可忽略 |

### POST `/note/xiaozhiChat`  流式问答

响应 `text/event-stream`。服务端固定按 `stream=true`。

相对创建会话**额外必填**：

| 字段 | 说明 |
|---|---|
| chatId 或 sessionId | 二选一 |
| contextId | 创建会话返回值 |
| query | 与创建会话同一句；追问则用新问题 |
| withReferences | `true` 时 SSE 可能带引用 |
| lastChatId | 仅断线续传，用上次事件 `id` |
| chatVersion | `"1"` 快速 / `"2"` 专家，默认 `"1"` |

SSE 事件名：

| event | 含义 |
|---|---|
| `text` | 回答增量。`id` 可用于续传 |
| `references` | 参考文档，元素含 `id`，再调 `qryXiaozhiReferences` |
| `done` | 正常结束，data 多为 `[DONE]` |
| `notData` | 范围内无内容 |
| `error` | 失败，data 为错误原文 |

```bash
curl -N -X POST "${ZHIZAI_BASE_URL}/note/xiaozhiChat" \
  -H "Authorization: ${ZHIZAI_REC_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"query":"找找关于支付的笔记","chatId":"...","contextId":"..."}'
```

### GET `/note/qryXiaozhiReferences`  引用详情

Query：`docIdList`，引用 id 逗号拼接，如 `1,2,3`。

`resultObject` 为笔记/文档详情列表，含 `noteId`、`name`、`summary` 等。不要把标题当成 `noteId`。

### GET `/note/clearXiaozhiCache`  清理流缓存

Query：`contextId`。
