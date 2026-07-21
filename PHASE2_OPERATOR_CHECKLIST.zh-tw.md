# Skill-0 Production Admission Phase 2 人工操作清單

本文件是 Phase 2 人工準備清單；英文版
[PHASE2_OPERATOR_CHECKLIST.md](PHASE2_OPERATOR_CHECKLIST.md) 為權威版本。

Production Admission 仍為 `WAITING_FOR_OPERATOR_EVIDENCE`。以下每個項目都必須
由授權人工操作員針對精確 production release 提供。不得以 test fixture、
repository example、AI 生成值、local image ID、mutable tag 或歷史證據代替。

## 人工提供需求

- [ ] Production environment identity（正式環境識別）。
- [ ] Trusted keyring location；其控制權必須與 evidence submitter 分離。
- [ ] 精確 API、Dashboard 與 Web 映像檔的不可變 deployed image digests。
- [ ] 從正式環境掛載 artifact 觀察並核准的 complete-tree model artifact digest。
- [ ] 綁定精確 release 與 environment 的最新 security evidence。
- [ ] 精確 release candidate 的最新 regression evidence。
- [ ] 精確 release candidate 與 environment boundary 的最新 production
  rehearsal evidence。
- [ ] 具備精確 `production-admission-approver` role 的授權操作員簽章。

## 簽署前的人工檢查

- [ ] Git commit 與 tree 乾淨，且符合 release candidate。
- [ ] Policy、Compose、trusted keyring、model 與 image digests 均符合 release
  binding。
- [ ] Evidence 完整、最新、未遭竄改、限定於指定 environment，並存放於
  repository 外的受保護儲存區。
- [ ] 簽署者未將 repository test fixture 當成 production evidence。
- [ ] 既有 verifier 在沒有 bypass 或 exception 的情況下回傳 `VERIFIED`。

## 禁止替代項目

AI Agent 不得建立或簽署 `production-admission-package.json`、捏造 operator
identity 或 signature、從本機範例推導 deployment digest，或把 synthetic
evidence（合成證據）描述為 production evidence。證據有缺漏時必須維持 blocked。
