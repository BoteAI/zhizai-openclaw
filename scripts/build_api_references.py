#!/usr/bin/env python3
"""维护脚本：用本地开放平台协议 Markdown 刷新各领域 references 的「接口协议」段。

保留每个文件「## 接口协议」之前的操作指引；仅替换协议正文。
协议文件路径可由环境变量 ZHIZAI_API_DOC 指定，默认同级目录旁的协议整理稿。
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = Path(os.environ.get("ZHIZAI_API_DOC", str(ROOT.parent / "open-platform-full-api.md")))
REF = ROOT / "references"


def split_parts(src: str) -> dict[str, str]:
    parts: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []
    for line in src.splitlines():
        if line.startswith("## ") and not line.startswith("### "):
            if current:
                parts[current] = "\n".join(buf).strip()
            current = line[3:].strip()
            buf = []
        elif current is not None:
            buf.append(line)
    if current:
        parts[current] = "\n".join(buf).strip()
    return parts


def slice_api(section: str, start: str, end: str | None = None) -> str:
    i = section.find(start)
    if i < 0:
        return ""
    if end:
        j = section.find(end, i + len(start))
        return section[i:j].strip() if j > 0 else section[i:].strip()
    return section[i:].strip()


def replace_protocol(path: Path, protocol: str) -> None:
    text = path.read_text(encoding="utf-8")
    marker = "## 接口协议"
    i = text.find(marker)
    if i < 0:
        raise RuntimeError(f"{path.name} missing '{marker}'")
    new_text = text[: i + len(marker)].rstrip() + "\n\n" + protocol.strip() + "\n"
    path.write_text(new_text, encoding="utf-8")
    print(f"updated protocol in {path.name}")


def main() -> int:
    if not SRC.exists():
        raise SystemExit(f"missing protocol doc: {SRC}")
    parts = split_parts(SRC.read_text(encoding="utf-8"))
    note = parts.get("笔记接口", "")

    note_before = slice_api(note, "### POST `/note/queryNoteList`", "### GET `/note/queryMySceneList`")
    note_create = slice_api(note, "### POST `/note/createNote`")
    scene_block = slice_api(note, "### GET `/note/queryMySceneList`", "### POST `/note/createNote`")
    know_q = parts.get("问小智 接口", "")
    file_q = parts.get("文件接口", "")

    replace_protocol(
        REF / "note.md",
        note_before + "\n\n" + note_create + "\n\n" + file_q + "\n\n" + know_q,
    )
    replace_protocol(REF / "scene.md", scene_block)
    replace_protocol(REF / "knowledge.md", parts.get("笔记集 接口", ""))
    replace_protocol(REF / "team.md", parts.get("团队 接口", ""))

    auth_sec = parts.get("鉴权 接口", "")
    replace_protocol(REF / "auth.md", auth_sec)

    msg_dev = (
        parts.get("消息 接口", "")
        + "\n\n"
        + parts.get("录音卡 接口", "")
        + "\n\n## 安全约束（强制）\n\n"
        "- `sendMessage`：发送前确认手机号与内容。\n"
        "- 录音卡批量最多 100 个 SN；关注 `notFoundSnList`。\n"
    )
    replace_protocol(REF / "msg-device.md", msg_dev)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
