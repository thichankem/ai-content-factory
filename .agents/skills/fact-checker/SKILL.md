---
name: fact-checker
description: Multi-source fact reconciliation and casualty statistics verification skill for historical disasters, aviation crashes, and natural catastrophes. Cross-references >=2 independent sources to eliminate hallucinations.
allowed-tools:
  - run_command
  - view_file
  - replace_file_content
---

# Fact Checker Skill — Cross-Source Disaster Verification

Historical and catastrophe content faces intense scrutiny from viewers, historians, and platform algorithms. A single hallucinated casualty figure or inaccurate date can destroy a channel's credibility.

This skill automates multi-source reconciliation using the Content Factory's native fact verification engine.

## 1. Direct API Endpoint

```bash
# Reconcile project facts against gathered research and attached documents
curl -X POST "http://127.0.0.1:8000/projects/{project_id}/facts/reconcile" \
  -H "Content-Type: application/json" \
  -d '{"claims": []}'
```

The system automatically extracts casualty figures, dates, and technical claims from:
- Primary research sources
- Attached Chronicling America historic news articles
- USGS earthquake records & Wikimedia archives
- Video narration script

## 2. Confidence Tagging Protocol

Every sensitive metric is classified into one of 4 tiers:
- `VERIFIED`: Confirmed across $\ge 2$ independent, reputable sources.
- `DISPUTED`: Different official bodies report conflicting numbers (e.g., direct impact deaths vs. long-term radiation sickness in Chornobyl).
- `ESTIMATED`: Witness approximation or archaeological estimate (e.g., Pompeii 79 AD).
- `UNVERIFIED`: Single source; requires disclaimer in narration.

## 3. Discrepancy Script Directives

When `DISPUTED` or `ESTIMATED` claims are detected:
- **Mandatory phrasing**: Script must use nuanced language:
  - *"Theo báo cáo của ủy ban điều tra..."*
  - *"Các nguồn thống kê đưa ra con số dao động từ X đến Y..."*
  - *"Hiện vẫn còn nhiều tranh cãi về nguyên nhân thực sự..."*
- **Never present conjecture as settled fact**: Clearly separate official investigation findings from alternative hypotheses.
