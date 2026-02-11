# External Skills Index

> 本文件索引 `C:\Dev\skills` 目錄下所有可用的 AI Agent Skills
> 
> 最後更新：2026-01-27
> 
> 由 skill-0 專案管理

## 目錄結構

```
C:\Dev\skills/
├── awesome-copilot/           # GitHub Copilot 社群 skills (~100+)
│   ├── instructions/          # .instructions.md 格式
│   ├── skills/               # SKILL.md 格式
│   └── collections/          # 技術棧集合
├── openai/                   # OpenAI Codex skills
│   └── skills/.system/       # 系統 skills (skill-installer)
├── Claude/                   # Anthropic Claude skills
│   ├── template/             # SKILL.md 模板
│   └── spec/                 # 規範文件
└── React-Next.js/            # Vercel React 最佳實踐
    └── skills/               # react-best-practices, web-design-guidelines
```

---

## 格式辨識

| 來源 | 格式 | 檔案命名 | Frontmatter |
|------|------|----------|-------------|
| **OpenCode/Claude/Codex** | `SKILL.md` | 資料夾名稱即 skill 名稱 | `name`, `description` |
| **Awesome-Copilot** | `.instructions.md` | `{skill-name}.instructions.md` | `description`, `applyTo` |
| **React-Next.js** | `SKILL.md` + `rules/*.md` | 資料夾結構 | `name`, `description` |

---

## 1. Awesome-Copilot Instructions (~100 個)

### 1.1 .NET / C# 系列

| Skill Name | 檔案 | 描述 | applyTo |
|------------|------|------|---------|
| csharp | `csharp.instructions.md` | Guidelines for building C# applications | `**/*.cs` |
| csharp-ko | `csharp-ko.instructions.md` | C# guidelines (Korean) | `**/*.cs` |
| csharp-ja | `csharp-ja.instructions.md` | C# guidelines (Japanese) | `**/*.cs` |
| csharp-mcp-server | `csharp-mcp-server.instructions.md` | MCP Server development in C# | `**/*.cs` |
| dotnet-wpf | `dotnet-wpf.instructions.md` | .NET WPF MVVM patterns | `**/*.xaml, **/*.cs` |
| dotnet-maui | `dotnet-maui.instructions.md` | .NET MAUI cross-platform | - |
| dotnet-maui-9-to-10-upgrade | `dotnet-maui-9-to-dotnet-maui-10-upgrade.instructions.md` | MAUI migration guide | - |
| dotnet-framework | `dotnet-framework.instructions.md` | .NET Framework legacy | - |
| dotnet-upgrade | `dotnet-upgrade.instructions.md` | .NET version upgrade guide | - |
| dotnet-architecture-good-practices | `dotnet-architecture-good-practices.instructions.md` | Clean architecture patterns | - |
| aspnet-rest-apis | `aspnet-rest-apis.instructions.md` | ASP.NET Core REST API | - |
| blazor | `blazor.instructions.md` | Blazor WebAssembly/Server | - |

### 1.2 Java 系列

| Skill Name | 檔案 | 描述 |
|------------|------|------|
| java | `java.instructions.md` | Java development guidelines |
| java-mcp-server | `java-mcp-server.instructions.md` | MCP Server in Java |
| java-11-to-java-17-upgrade | `java-11-to-java-17-upgrade.instructions.md` | Java 11→17 migration |
| java-17-to-java-21-upgrade | `java-17-to-java-21-upgrade.instructions.md` | Java 17→21 migration |
| java-21-to-java-25-upgrade | `java-21-to-java-25-upgrade.instructions.md` | Java 21→25 migration |

### 1.3 JavaScript/TypeScript 系列

| Skill Name | 檔案 | 描述 |
|------------|------|------|
| typescript-5-es2022 | `typescript-5-es2022.instructions.md` | TypeScript 5 + ES2022 |
| typescript-mcp-server | `typescript-mcp-server.instructions.md` | MCP Server in TypeScript |
| nodejs-javascript-vitest | `nodejs-javascript-vitest.instructions.md` | Node.js + Vitest testing |
| angular | `angular.instructions.md` | Angular framework |
| vuejs3 | `vuejs3.instructions.md` | Vue.js 3 composition API |
| nextjs | `nextjs.instructions.md` | Next.js framework |
| nextjs-tailwind | `nextjs-tailwind.instructions.md` | Next.js + Tailwind CSS |
| nestjs | `nestjs.instructions.md` | NestJS backend framework |
| astro | `astro.instructions.md` | Astro static site generator |
| azure-functions-typescript | `azure-functions-typescript.instructions.md` | Azure Functions + TS |

### 1.4 Python 系列

| Skill Name | 檔案 | 描述 |
|------------|------|------|
| langchain-python | `langchain-python.instructions.md` | LangChain framework |
| dataverse-python | `dataverse-python.instructions.md` | Dataverse SDK Python |
| dataverse-python-* | (14 個相關) | Dataverse 專項指南 |
| copilot-sdk-python | `copilot-sdk-python.instructions.md` | Copilot SDK Python |

### 1.5 其他語言

| Skill Name | 檔案 | 描述 |
|------------|------|------|
| go | `go.instructions.md` | Go development |
| go-mcp-server | `go-mcp-server.instructions.md` | MCP Server in Go |
| kotlin-mcp-server | `kotlin-mcp-server.instructions.md` | MCP Server in Kotlin |
| clojure | `clojure.instructions.md` | Clojure functional |
| dart-n-flutter | `dart-n-flutter.instructions.md` | Dart & Flutter mobile |
| apex | `apex.instructions.md` | Salesforce Apex |
| lwc | `lwc.instructions.md` | Lightning Web Components |
| coldfusion-cfc | `coldfusion-cfc.instructions.md` | ColdFusion components |
| coldfusion-cfm | `coldfusion-cfm.instructions.md` | ColdFusion templates |

### 1.6 Cloud/DevOps 系列

| Skill Name | 檔案 | 描述 |
|------------|------|------|
| terraform | `terraform.instructions.md` | Terraform IaC |
| terraform-azure | `terraform-azure.instructions.md` | Terraform + Azure |
| terraform-sap-btp | `terraform-sap-btp.instructions.md` | Terraform + SAP BTP |
| kubernetes-manifests | `kubernetes-manifests.instructions.md` | K8s YAML manifests |
| kubernetes-deployment-best-practices | `kubernetes-deployment-best-practices.instructions.md` | K8s deployment patterns |
| containerization-docker-best-practices | `containerization-docker-best-practices.instructions.md` | Docker best practices |
| azure-devops-pipelines | `azure-devops-pipelines.instructions.md` | Azure DevOps CI/CD |
| github-actions-ci-cd-best-practices | `github-actions-ci-cd-best-practices.instructions.md` | GitHub Actions |
| ansible | `ansible.instructions.md` | Ansible automation |
| bicep-code-best-practices | `bicep-code-best-practices.instructions.md` | Azure Bicep IaC |
| azure-verified-modules-terraform | `azure-verified-modules-terraform.instructions.md` | Azure verified modules |
| azure-verified-modules-bicep | `azure-verified-modules-bicep.instructions.md` | Azure verified modules |

### 1.7 Database 系列

| Skill Name | 檔案 | 描述 |
|------------|------|------|
| ms-sql-dba | `ms-sql-dba.instructions.md` | SQL Server DBA |
| mongo-dba | `mongo-dba.instructions.md` | MongoDB DBA |

### 1.8 Best Practices / 通用

| Skill Name | 檔案 | 描述 |
|------------|------|------|
| a11y | `a11y.instructions.md` | Accessibility guidelines |
| code-review-generic | `code-review-generic.instructions.md` | Code review patterns |
| devops-core-principles | `devops-core-principles.instructions.md` | DevOps principles |
| ai-prompt-engineering-safety-best-practices | `ai-prompt-engineering-safety-best-practices.instructions.md` | AI safety |
| memory-bank | `memory-bank.instructions.md` | Context memory patterns |
| markdown | `markdown.instructions.md` | Markdown writing |
| localization | `localization.instructions.md` | i18n/l10n |
| html-css-style-color-guide | `html-css-style-color-guide.instructions.md` | HTML/CSS styling |

### 1.9 Power Platform / M365

| Skill Name | 檔案 | 描述 |
|------------|------|------|
| azure-logic-apps-power-automate | `azure-logic-apps-power-automate.instructions.md` | Logic Apps + Power Automate |
| declarative-agents-microsoft365 | `declarative-agents-microsoft365.instructions.md` | M365 Declarative Agents |
| mcp-m365-copilot | `mcp-m365-copilot.instructions.md` | MCP + M365 Copilot |
| pcf-* | (8 個相關) | Power Platform PCF 控件 |

### 1.10 MCP Server 開發

| Skill Name | 檔案 | 描述 |
|------------|------|------|
| csharp-mcp-server | `csharp-mcp-server.instructions.md` | C# MCP Server |
| go-mcp-server | `go-mcp-server.instructions.md` | Go MCP Server |
| java-mcp-server | `java-mcp-server.instructions.md` | Java MCP Server |
| kotlin-mcp-server | `kotlin-mcp-server.instructions.md` | Kotlin MCP Server |
| typescript-mcp-server | `typescript-mcp-server.instructions.md` | TypeScript MCP Server |

---

## 2. Awesome-Copilot Skills (SKILL.md 格式)

| Skill Name | 路徑 | 描述 |
|------------|------|------|
| webapp-testing | `skills/webapp-testing/SKILL.md` | Playwright web testing toolkit |

---

## 3. OpenAI/Codex Skills

| Skill Name | 路徑 | 描述 |
|------------|------|------|
| skill-installer | `skills/.system/skill-installer/SKILL.md` | Install skills from GitHub repos |

---

## 4. Claude Skills

| Skill Name | 路徑 | 描述 |
|------------|------|------|
| template | `template/SKILL.md` | SKILL.md 模板範例 |

規範文件：`spec/agent-skills-spec.md` → https://agentskills.io/specification

---

## 5. React-Next.js Skills

### 5.1 React Best Practices (45 Rules)

| Skill Name | 路徑 | 描述 |
|------------|------|------|
| vercel-react-best-practices | `skills/react-best-practices/SKILL.md` | Vercel React/Next.js 性能優化 |

**規則分類 (Priority)：**

| Priority | Category | 數量 | Prefix |
|----------|----------|------|--------|
| 1 | Eliminating Waterfalls | 5 | `async-` |
| 2 | Bundle Size Optimization | 5 | `bundle-` |
| 3 | Server-Side Performance | 5 | `server-` |
| 4 | Client-Side Data Fetching | 2 | `client-` |
| 5 | Re-render Optimization | 7 | `rerender-` |
| 6 | Rendering Performance | 7 | `rendering-` |
| 7 | JavaScript Performance | 12 | `js-` |
| 8 | Advanced Patterns | 2 | `advanced-` |

### 5.2 Web Design Guidelines

| Skill Name | 路徑 | 描述 |
|------------|------|------|
| web-design-guidelines | `skills/web-design-guidelines/SKILL.md` | UI/UX design patterns |

### 5.3 Vercel Deploy (Claude.ai)

| Skill Name | 路徑 | 描述 |
|------------|------|------|
| vercel-deploy-claimable | `skills/claude.ai/vercel-deploy-claimable/SKILL.md` | Vercel deployment skill |

---

## 6. Collections (技術棧組合)

Awesome-Copilot 的 Collections 將多個 instructions 打包成技術棧組合：

| Collection | 檔案 | 包含技術 |
|------------|------|----------|
| csharp-dotnet-development | `csharp-dotnet-development.md` | C#, ASP.NET, Entity Framework |
| java-development | `java-development.md` | Java, Spring Boot |
| frontend-web-dev | `frontend-web-dev.md` | React, Vue, Angular, CSS |
| azure-cloud-development | `azure-cloud-development.md` | Azure services, ARM/Bicep |
| devops-oncall | `devops-oncall.md` | K8s, Docker, monitoring |
| database-data-management | `database-data-management.md` | SQL, MongoDB, Redis |
| csharp-mcp-development | `csharp-mcp-development.md` | C# MCP Server stack |
| typescript-mcp-development | `typescript-mcp-development.md` | TS MCP Server stack |
| python-mcp-development | `python-mcp-development.md` | Python MCP Server stack |
| go-mcp-development | `go-mcp-development.md` | Go MCP Server stack |

---

## 格式轉換規範

### Awesome-Copilot → OpenCode SKILL.md

**輸入格式 (.instructions.md):**
```yaml
---
description: 'Guidelines for building C# applications'
applyTo: '**/*.cs'
---
```

**輸出格式 (SKILL.md):**
```yaml
---
name: csharp
description: Guidelines for building C# applications. Use when writing, reviewing, or refactoring C# code. Triggers on .cs files.
---
```

**轉換規則：**
1. `name`: 從檔名取得 (`xxx.instructions.md` → `xxx`)
2. `description`: 保留原始 + 補充 "Use when..." + "Triggers on {applyTo}"
3. 移除 `applyTo`（OpenCode 不使用此欄位）
4. 保留 body 內容

---

## 統計

| 來源 | Skills 數量 | 格式 |
|------|------------|------|
| Awesome-Copilot Instructions | ~100 | `.instructions.md` |
| Awesome-Copilot Skills | 1 | `SKILL.md` |
| OpenAI/Codex | 1 | `SKILL.md` |
| Claude | 1 (template) | `SKILL.md` |
| React-Next.js | 3 | `SKILL.md` |
| **總計** | **~106** | - |

---

## 相關連結

- [Agent Skills Spec](https://agentskills.io/specification)
- [Awesome Copilot GitHub](https://github.com/github/awesome-copilot)
- [OpenAI Skills GitHub](https://github.com/openai/skills)
- [Anthropic Skills GitHub](https://github.com/anthropics/skills)
