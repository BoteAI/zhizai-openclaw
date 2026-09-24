# 智在记录 · 鉴权

负责把“用户想用智在记录”推进到可调业务接口的状态。不要只说“已配置”：Key 非空且至少一次业务调用 `resultCode=0` 才算连接成功。

本模块 **没有独立鉴权接口**。不要调用 `getApiKeyByPassword`、`getApiKeyBySmsCode`、`sendPhoneSms`、`analysisToken`。API Key 由用户在开发者后台自行配置到环境变量。

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

## 首次连接闭环

1. 检查智能体/环境中的 `ZHIZAI_REC_API_KEY` 是否已配置且非空。
2. 未配置：只提示前往 [智在记录开发者](https://www.zzjilu.com/pc/developer) 获取并配置；不调业务接口。
3. 无写入验收：`POST /note/queryNoteList`，`pageNum=1`、`pageSize=1`。成功才可宣布已连接。
4. 不要向用户索要口令或短信验证码来换 Key。

## 安全与恢复

- 不展示或记录完整 `Authorization` / API Key；调试仅掩码。
- 鉴权失败引导检查环境变量，不回显 Header。HTTP 401 空 body：Key 未勾选该接口。
- 部分接口若返回「缺失应用 ID」，补 Header `APP-ID`，取值来自 `uploadSingleFile.resultObject.appId` 或 `ZHIZAI_APP_ID`。
