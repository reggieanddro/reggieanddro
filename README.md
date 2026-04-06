<div align="center">

![Jesse Niesen](https://img.shields.io/badge/Jesse_Niesen-000000?style=for-the-badge&logoColor=white)
![CEO & Sole Founder](https://img.shields.io/badge/CEO_%26_Sole_Founder-22FF00?style=for-the-badge&logoColor=000000)
![US Marine Corps Veteran](https://img.shields.io/badge/US_Marine_Corps_Veteran-000000?style=for-the-badge&logoColor=22FF00)

### Reggie & Dro LLC | San Antonio, TX

Building **[Liv Hana](https://livhana.ai)** — a strategic intelligence platform that ships autonomous compliance, multi-model AI verification, and real-time voice orchestration for regulated industries.

[![API Docs](https://img.shields.io/badge/API_Docs-LivHana.ai-22FF00?style=flat-square&labelColor=000000)](https://livhana.ai)
[![Contact](https://img.shields.io/badge/Contact-high%40reggieanddro.com-22FF00?style=flat-square&labelColor=000000)](mailto:high@reggieanddro.com)
[![Site](https://img.shields.io/badge/Site-JesseNiesen.com-22FF00?style=flat-square&labelColor=000000)](https://jesseniesen.com)

</div>

---

<!-- STATS_START -->
### 📊 April 2026 Live Stats (Solo, No CS Degree)

> **🤖 Auto-Updated:** Sunday, April 05, 2026 at 10:20 PM CT
> **📅 Day 6 of 30**
 | **🔥 Peak Day:** 05 with 462 contributions

| Metric | Value | vs Google L5 Engineer | Multiplier |
|--------|-------|----------------------|------------|
| **Total Contributions** | 1,134 | 40-80/mo | **14.2-28.4x** |
| **Commits** | 1,131 | 40-80/mo | **14.1-28.3x** |
| **Daily Average** | 189.0 | 2-4/day | **47.2-94.5x** |
| **Days Active (rate)** | 6/6 | 18-22/mo | **1.4-1.7x** |
| **Projected Month** | ~5,670 | 40-80/mo | **70.9-141.8x** |

<details>
<summary>📈 Daily Breakdown (Click to expand)</summary>

```
01: ███████░░░░░░░░░░░░░ 183
02: ███████░░░░░░░░░░░░░ 164
03: ███████░░░░░░░░░░░░░ 179
04: ██████░░░░░░░░░░░░░░ 145
05: ████████████████████ 462
06: ░░░░░░░░░░░░░░░░░░░░ 1
```

</details>

🔥 **Current Streak:** 15 consecutive days with contributions
📈 **MoM Trend:** +106.9% vs March (2,741 actual → ~5,670 projected)

**Source:** [GitHub GraphQL API](https://docs.github.com/graphql) (live) • [2025 Worklytics Software Engineering Productivity Benchmarks](https://www.worklytics.co/resources/software-engineering-productivity-benchmarks-2025-good-scores)

<!-- STATS_END -->


## What is Liv Hana SI?

Liv Hana is a cloud-native strategic intelligence platform built on GCP Cloud Run, AlloyDB (PostgreSQL + pgvector), and a 5-model LLM Council. It provides deterministic compliance verification, probabilistic AI reasoning, and sub-500ms voice synthesis — all through clean REST APIs.

**Architecture:** 9 production Cloud Run services, 839+ database tables, 557 migrations, 142-point automated verification (RALPH), zero-Docker serverless deploys via GCS Buildpacks.

**Built solo. No team. No CS degree. Marine discipline + AI-native from day one.**

---

## API Products

### RALPH CaaS — Compliance-as-a-Service

> 50-state hemp regulatory compliance verification API

```
POST /api/v1/compliance/verify
Content-Type: application/json

{
  "product_id": "sku-001",
  "state": "TX",
  "thc_coa_url": "https://lab.example.com/coa/12345"
}
```

- Real-time verification against state-by-state hemp regulations
- COA (Certificate of Analysis) validation and THC threshold enforcement
- Age-gate integration (21+ fail-closed enforcement)
- DSHS license compliance tracking
- 142-hook automated verification pipeline

![Compliance](https://img.shields.io/badge/50--State_Coverage-22FF00?style=flat-square&labelColor=000000)
![Fail-Closed](https://img.shields.io/badge/Fail--Closed_Architecture-22FF00?style=flat-square&labelColor=000000)

---

### LLM Council + Agent Gateway

> Multi-model AI verification and orchestration API

```
POST /api/v1/council/agent-review
Content-Type: application/json

{
  "task": "verify-deployment",
  "payload": { "service": "integration-service", "revision": "01583-rds" },
  "quorum": 3
}
```

- 5-seat council: Claude, GPT, Codex, Gemini, Grok — direct API, no middleware
- Consensus voting with configurable quorum thresholds
- Agent orchestration with stateful task management
- Thompson sampling for optimal model routing
- Constitutional governance with cryptographic audit trail

![5-Model Council](https://img.shields.io/badge/5--Model_Council-22FF00?style=flat-square&labelColor=000000)
![Direct API](https://img.shields.io/badge/Direct_Provider_APIs-22FF00?style=flat-square&labelColor=000000)

---

### Voice AI Orchestration

> Real-time voice synthesis and conversation API

```
POST /api/v1/voice/session
Content-Type: application/json

{
  "mode": "commerce",
  "language": "en-US",
  "cascade": ["gemini-live", "gemini-flash", "claude-sonnet"]
}
```

- Sub-500ms end-to-end voice latency with barge-in support
- Multi-tier model cascade with automatic failover
- Real-time STT/TTS pipeline (Deepgram + ElevenLabs)
- Voice-driven commerce workflows
- WebSocket streaming for continuous conversation

![Sub-500ms Latency](https://img.shields.io/badge/Sub--500ms_Latency-22FF00?style=flat-square&labelColor=000000)
![WebSocket](https://img.shields.io/badge/WebSocket_Streaming-22FF00?style=flat-square&labelColor=000000)

---

## Stack

```
COMPUTE    Cloud Run (9 services) · GCS Buildpacks · GitHub Actions CI/CD
DATA       AlloyDB (PostgreSQL + pgvector) · BigQuery · Cloud Storage
RUNTIME    Node.js · TypeScript · Next.js · Python · FastAPI · DSPy
AI         Claude · GPT · Codex · Gemini · Grok (direct API)
VOICE      Gemini Live · Deepgram STT · ElevenLabs TTS
COMMERCE   LightSpeed · Authorize.net · Klaviyo · Twilio
SECURITY   Auth0 · Secret Manager · Cloudflare WAF · Veriff (age verification)
```

---

## Output

| Metric | Value |
|--------|-------|
| **Commits (2026 YTD)** | 4,931+ |
| **Cloud Run Services** | 9 production |
| **Database Tables** | 839+ |
| **Migrations Shipped** | 557 |
| **RALPH Hooks** | 142 passing, 0 failing |
| **Cloud Schedulers** | 117+ |
| **Customers** | 13,347 |

---

## 4 Lines of Business

| Entity | Domain |
|--------|--------|
| **Reggie & Dro** | Hemp commerce + retail (DSHS License #690) |
| **High Noon Cartoon** | Media + entertainment |
| **One Plant Solution** | Education + advocacy |
| **Herbitrage** | Technology + incubation |

---

## Connect

| | |
|---|---|
| **API & Docs** | [LivHana.ai](https://livhana.ai) |
| **Email** | [high@reggieanddro.com](mailto:high@reggieanddro.com) |
| **Web** | [JesseNiesen.com](https://jesseniesen.com) |
| **Location** | San Antonio, Texas |

---

<div align="center">

![Profile Views](https://komarev.com/ghpvc/?username=reggieanddro&color=brightgreen&style=flat-square&label=views)

*Self-taught. Mission-driven. Shipping autonomously.*

</div>
