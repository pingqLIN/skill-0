# Runtime Asset P0.1 操作就緒計畫

- 狀態：**技術驗收完成；operator authority 維持 NO-GO**
- 日期：`2026-07-18`
- 權威邊界：Runtime v4 維持 dry-run only；P0 contract 保持 additive
- 英文權威版本：[`runtime-asset-p0-1-operational-readiness-plan.md`](runtime-asset-p0-1-operational-readiness-plan.md)

## 目標

在不捏造 Governance approval 的前提下，補齊已驗證 P0 與可用本機 derived
Index 之間的操作缺口。Public checkout 沒有 operator authority DB；根目錄的
`skills.db` 與 `governance.db` 都只是無關的 sample DB。

## 批次

1. **P0.1-A identity：**依三份 Java upgrade payload 的明確來源 identity 產生
   唯一 canonical Asset IDs，同時保留共用 ambiguous legacy alias 與原始 payload。
2. **P0.1-B maintenance tooling：**加入 Index preflight、migration preview、
   verified backup、apply、incremental index、第二次 no-op 與 doctor evidence。
3. **P0.1-C rehearsal：**先對 disposable copy 演練；備份與驗證通過後才建立
   可重建的 local Index。
4. **P0.1-D acceptance：**執行 contract、compatibility、migration、search、
   Runtime、schema、文件與完整 regression gates。

## Authority 邊界

`governance/db/governance.db` 是唯一 operator Governance path。P0.1 不會複製
根目錄 sample DB、不會合成 binding，也不會為了 doctor 變綠而批准 revisions。
因此 identity 與 Index projection 健康時，本機 doctor 仍可能是
`authority-missing`。只有 approved Governance fixture，或完成真實 review 的
operator store，才要求 `healthy`／exit 0。

## Rollback

任何 operator Index mutation 前都必須建立並驗證 SQLite backup。舊 target
只有在確認它是 derived Index 且已保留後才能替換。Rollback 必須在 writers
停止時還原 verified backup，不能原地 drop tables。Governance 與 Runtime store
都不執行 migration。

## 執行紀錄

- `P0.1-A` 已完成：Java canonical Asset IDs、ambiguous legacy alias 相容、
  全域 identity collision 拒絕，以及 API 到 Governance 的 canonical identity
  傳遞都已通過 focused review 與測試。
- `P0.1-B` 已完成：operator maintenance CLI 會在無效 Index schema 上於
  migration 前失敗、建立不覆寫且 verified 的 backup、保留 checksum evidence，
  並在 authority／canonical／unknown failure 存在時於 indexing 前阻擋。預設只有
  post-index doctor healthy 才成功；明確的 non-healthy rehearsal 仍標記為未接受。
- `P0.1-C` 已完成：disposable 與 root derived Index 都通過 preview、verified
  backup、migration、restore、196-row incremental index、第二次 no-op、
  integrity 與 semantic-search smoke。因為沒有 operator Governance DB，本機
  doctor 仍誠實維持 authority-missing。
- `P0.1-D` 已完成：test-only full-corpus acceptance fixture 將 196 個 canonical
  revisions 綁定至相符的 approved-current Governance 證據與已套用的 checksum
  migration。Read-only doctor 回傳 `healthy`／0，Registry 與 Index 都是 196
  rows。這證明技術驗收路徑成立，但不會建立或取代 operator review decisions。
