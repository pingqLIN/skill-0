# Security Policy

## 支援邊界

Security maintenance 涵蓋 maintained mainline 上的 Runtime Architecture v1 stable foundation：single-host deployment、唯一支援的 Runtime Asset type（`skill`），以及 dry-run-only Runtime API behavior。

Historical snapshots、unmaintained branches、modified deployments、real adapter execution，以及超出文件邊界的 topologies，都不包含在 production-readiness claim 內。

權威 deployment policy 是 [`docs/production-security-policy.md`](docs/production-security-policy.md)。英文 [`SECURITY.md`](SECURITY.md) 為權威文件。

## 回報 vulnerability

若 repository Security tab 提供 private vulnerability-reporting channel，請使用該管道。若無此管道，請透過 repository profile 所列的私人方式聯絡 owner。不得在 public issue 發布 exploit details、secrets、credentials、customer data 或可執行 proof of concept。

回報內容應包含 affected commit 或 version、deployment boundary、reproduction conditions、impact，以及最小且已 redacted 的 proof。Maintainers 會分類 report、保存 evidence，並協調 remediation 與 disclosure。Vulnerability report 永遠不授權存取資料、干擾 deployment，或測試非本人已授權的 systems。
