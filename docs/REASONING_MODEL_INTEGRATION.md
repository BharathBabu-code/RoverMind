# RoverMind — Meta Reasoning Model Integration Guide

This document details the architectural integration, verification, and execution lifecycle of the second Meta AI model powering RoverMind's **Mission Intelligence and Reasoning Layer**.

---

## 1. Architectural Role & Separation of Concerns

RoverMind adheres strictly to the separation of visual perception, deterministic path mathematics, and contextual reasoning:

```
+-------------------------------------------------------------------------+
|                  1. VISUAL PERCEPTION (Meta SAM 3.1)                    |
|   Promptable pixel segmentation, token grammar parsing, mask extraction  |
+-------------------------------------------------------------------------+
                                    ↓
+-------------------------------------------------------------------------+
|             2. DETERMINISTIC ENGINE (Backend Python Core)               |
|   Normalized terrain classification, impedance costmaps, custom A*      |
+-------------------------------------------------------------------------+
                                    ↓
+-------------------------------------------------------------------------+
|             3. MISSION REASONING LAYER (Meta Llama / Reasoning)         |
|   Observation briefing synthesis, route justification, tool-based chat  |
+-------------------------------------------------------------------------+
```

### Core Non-Negotiables:
- **No Hallucinated Ground Truth**: The reasoning model does not create terrain categories or path metrics. It interprets structured telemetry produced deterministically by the backend.
- **Independent Operability**: If the reasoning model is unconfigured or unavailable, RoverMind automatically falls back to its deterministic rule engine.
- **Bounded Computation**: All model requests enforce strict timeouts (`httpx.Timeout(30.0, connect=10.0)`), bounded context tokens, and a maximum of 4 tool-calling iterations.

---

## 2. Model Selection & API Compatibility

### Supported Reasoning Models:
1. **`llama-3.3-70b-instruct` (Default Recommended)**:
   - Meta's premier open reasoning and instruction-tuned model.
   - Native support for JSON Schema structured outputs and function/tool calling.
   - Served via OpenAI-compatible endpoints (`https://api.meta.ai/v1`).
2. **`llama-3.1-70b-instruct` / `llama-3.1-8b-instruct`**:
   - Fully compatible drop-in alternatives for varying resource or latency requirements.
3. **`muse-spark` (Candidate Evaluation)**:
   - Reserved as an alternative multimodal reasoning model. If chosen, configure `META_REASONING_MODEL=muse-spark` in `.env`.

---

## 3. Configuration & Four Operational States

RoverMind supports four distinct operational configurations:

| State | SAM 3.1 Status | Reasoning Model Status | UI Telemetry Badges |
|---|---|---|---|
| **1. Dual Offline (Default)** | Offline Synthetic | Deterministic Rule Engine | Amber: `⚡ OFFLINE SYNTHETIC DEMO` & `DETERMINISTIC ASSISTANT` |
| **2. SAM Only** | Live SAM 3.1 | Deterministic Rule Engine | Green: `● LIVE SAM 3.1 ACTIVE` & Amber: `DETERMINISTIC ASSISTANT` |
| **3. Reasoning Only** | Offline Synthetic | Live Meta Reasoning (Llama) | Amber: `⚡ OFFLINE SYNTHETIC DEMO` & Green: `● LIVE META REASONING` |
| **4. Dual Live Active** | Live SAM 3.1 | Live Meta Reasoning (Llama) | Green: `● LIVE SAM 3.1 ACTIVE` & Green: `● LIVE META REASONING` |

### Environment Variables:
```env
# Meta SAM 3.1 Key
META_API_KEY=

# Meta Reasoning Model Configuration (defaults to META_API_KEY if omitted)
META_REASONING_API_KEY=
META_REASONING_MODEL=llama-3.3-70b-instruct
META_REASONING_BASE_URL=https://api.meta.ai/v1
```

---

## 4. Automated Observation Briefing Generation

The briefing service (`backend/app/services/reasoning_service.py`) synthesizes four structured sections:

1. **Observation Overview**: Dominant terrain class, detected concept labels, spatial highlights, and cell distribution percentages.
2. **Navigation Assessment**: Feasibility determination (`FEASIBLE` or `UNFEASIBLE`), waypoints count, total weighted traversal cost, geometric length, and obstacle avoidance factor.
3. **Risk & Uncertainty**: High-cost regolith zones (sand drifts, rocky outcrops), unmapped cell percentages, and explicit monocular sensor limitations.
4. **Mission Takeaways**: Concise operator action items for rover ground teams.

### Graceful Fallback:
When `settings.is_reasoning_api_configured` is `False` or if the network request fails, `generate_deterministic_briefing()` produces an identical schema from backend telemetry, attributed with `source_model="deterministic-rule-engine"` and `is_ai_generated=False`.

---

## 5. Security & Isolation Safeguards

1. **Zero Secret Leakage**: `META_REASONING_API_KEY` is kept strictly in server memory and never exposed to the browser or logged in diagnostic strings.
2. **Mission Isolation**: Chat requests require an `image_id`. The server validates that the `image_id` matches an active analysis in `_ANALYSIS_STORE` before executing queries.
3. **Bounded Memory**: Conversations are capped to `MAX_MESSAGES_PER_CONVERSATION = 20` messages and `MAX_CONVERSATIONS = 25` sessions.
