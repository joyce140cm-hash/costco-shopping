# CLAUDE.md

## 任務委派

- 複雜或多步驟的任務交給 sub-agent 處理；簡單的查詢與小修改可以直接自己做。
- 不要所有任務都使用 Fable，較簡單的任務請使用 Opus。
- 每個任務交給一個 sub-agent，執行前先規劃。
- 彼此獨立的 sub-agent 任務要平行執行。
- 委派出去的任務，以 sub-agent 的報告為主，避免重複讀取同樣的檔案。

## 模型路由

呼叫 Agent 時都必須指定 `model`（可用值：`fable`、`opus`、`haiku`）。

- **Fable**（Fable 5.1）：系統架構、困難的 Bug、程式碼審查
- **Opus**（Opus 5.5）：修改、測試、文件、重構
- **Haiku**（Haiku 5.5）：資料查詢與摘要
