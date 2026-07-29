# Day 04 Lab v2 Report - Research Agent

## Team

- Team: Group 26
- Members: update before submit
- Provider/model: Gemini, `gemini-3.5-flash-lite`

---

# PHAN A - Gioi thieu agent

## A1. Agent nay lam duoc gi

Research agent nay ho tro tim tin web/news, doc URL, tim bai dang Twitter/X theo tai khoan hoac chu de, tim paper/chinh sach noi bo, kiem tra chat luong nguon, va tong hop thanh digest markdown. Agent uu tien routing dung tool, dung args, hoi lai khi thieu thong tin, va xac nhan truoc khi gui Telegram.

**Link dung thu:**

- UI chua xay trong moc pre-UI.
- Local CLI: `python chat.py --provider gemini --version v3`

## A2. Tool agent co

| Ten tool | Lam duoc gi | Tool moi nhom them? |
|---|---|---|
| clarify | Hoi lai khi thieu account/URL/topic hoac can xac nhan yes/no truoc action | khong |
| timeline | Lay bai dang gan day cua mot account Twitter/X cu the | khong |
| social_search | Tim bai dang Twitter/X theo keyword/topic | khong |
| lookup | Tim web/news theo query, topic, timeframe | khong |
| fetch | Doc noi dung mot URL cu the | khong |
| format | Render cac item da co thanh markdown digest | khong |
| send | Gui text len Telegram sau khi da duoc xac nhan | khong |
| policy | Tim trong company policy markdown | khong |
| papers | Tim paper tren arXiv | khong |
| paper_text | Trich text tu paper arXiv cu the | khong |
| source_check | Kiem tra heuristic chat luong/rui ro citation cua danh sach URL/domain | co |

## A3. Cau hoi mau de thu

1. Tin tuc AI hom nay co gi noi bat?
2. Lay 5 tweet moi nhat cua Sam Altman.
3. Tom tat bai nay giup minh: https://example.com/ai-policy
4. Kiem tra 2 nguon nay co on de trich dan khong: https://openai.com/research va https://medium.com/example/ai-notes
5. Dang ban tin nay len Telegram giup minh.

## A4. Kich ban demo da rehearse

| Scenario | Tool trace can thay | Cau chuyen cai thien version | Fallback run/transcript |
|---|---|---|---|
| Tin AI hom nay | `lookup(query=AI, topic=news, timeframe=day)` | v0 sai nhieu args/routing; v3 base pass 20/20 | `runs/v3_B_base_gemini_20260729T155303255458.json` |
| Thieu URL khi tom tat bai viet | `clarify(response_type=text)` | v3 ep schema `clarify.response_type` de khong thieu arg | `runs/v3_B_base_gemini_20260729T155303255458.json` |
| Kiem tra nguon | `source_check(sources=[...])` | v3 them tool moi cua nhom va group eval pass 10/10 | `runs/v3_B_group_gemini_20260729T155622896451.json` |

---

# PHAN B - Chi tiet / Bang chung

Metric hop le khi `provider_error_cases=0` va `measured_cases=total_cases`. v1 co provider error do quota/network Gemini, nen chi dung lam evidence ve artifact/prompt change; v2 va v3 la metric hop le.

## B1. Version evidence

| Version | Prompt/tool change | Hypothesis | Metric name | Before | After | Run File |
|---|---|---|---|---:|---:|---|
| v0 | Baseline starter prompt + vague tools | Starter se sai routing/args/boundary | case_accuracy |  | 0.60 | `runs/v0_B_base_gemini_20260729T150444184264.json` |
| v1 | Sua `system_prompt.md`: routing, missing-info, out-of-scope, confirmation | Prompt ro hon se giam loi tool/arg | case_accuracy | 0.60 | 1.00 measured only, provider_error=3 | `runs/v1_B_base_gemini_20260729T152818925363.json` |
| v2 | Sua `tools.yaml`: description + argument conventions | Tool declaration ro hon se on dinh args | case_accuracy | 0.60 | 0.95 | `runs/v2_B_base_gemini_20260729T153116045600.json` |
| v3 | Them `source_check`, group eval, ep `clarify.response_type`, siết lookup query/confirmation | Tool moi khong lam nhieu core routing va group eval pass | case_accuracy | 0.95 | 1.00 base; 1.00 group | `runs/v3_B_base_gemini_20260729T155303255458.json`; `runs/v3_B_group_gemini_20260729T155622896451.json` |

## B2. Failure analysis

| Case ID | Failure Type | Actual Tool Calls | What Failed | Fix |
|---|---|---|---|---|
| v0 multiple cases | wrong_tool / missing_info / wrong_boundary / out_of_scope / wrong_arg_value | mixed | Starter prompt encouraged guessing, one-step action, and vague tool choice | v1 rewrote system prompt with explicit routing and boundaries |
| R11_missing_url in v2 | missing_info | `clarify` | Model omitted or mismatched `response_type=text` | v3 made `clarify.response_type` required in schema |
| R12_confirm_before_send during v3 iteration | wrong_boundary | `clarify(response_type=text)` | Send/Telegram request needed yes/no confirmation | v3 prompt explicitly maps send/post/publish/Telegram to `response_type=yes_no` |
| G03_web_news_month during v3 iteration | wrong_arg_value | `lookup` | Model included time/news words inside query | v3 prompt says lookup query contains only the main subject; topic/timeframe carry news/time |

## B3. Team eval cases

| Case ID | What It Tests | Expected Tool/Behavior | Result |
|---|---|---|---|
| G01_source_check_urls | Source credibility/citation request with URLs | `source_check` | PASS |
| G02_fetch_specific_url | Concrete URL reading | `fetch` | PASS |
| G03_web_news_month | Web news timeframe month | `lookup(topic=news,timeframe=month)` | PASS |
| G04_missing_account | Vague account | `clarify(response_type=text)` | PASS |
| G05_confirm_publish | Telegram send boundary | `clarify(response_type=yes_no)` | PASS |
| G06_multiturn_source_check | Carry URLs across turns | `source_check` | PASS |
| G07_multiturn_limit_correction | Carry handle, correct limit | `timeline(screenname=sama,limit=4)` | PASS |
| G08_multiturn_missing_url_then_url | Missing URL then provided URL | `fetch` | PASS |
| G09_multiturn_switch_social_to_web | Switch from Twitter to web news | `lookup` | PASS |
| G10_multiturn_out_of_scope | Coding request outside scope | no tool | PASS |

## B4. Live chat evidence

| Scenario/Turn | Version | Tool Calls + Args | Transcript/Run | Outcome |
|---|---|---|---|---|
| Normal research: "Tin AI hom nay co gi noi bat?" | v3 | `lookup(query=AI, topic=news, timeframe=day)` then `format(template=daily_ai_vn)` | `transcripts/v3_gemini_20260729T160109179718.transcript.json` | Returned a Vietnamese AI news digest with sources |
| Missing URL: "Tom tat bai viet nay giup minh" | v3 | `clarify(response_type=text)` | `transcripts/v3_gemini_20260729T160109179718.transcript.json` | Asked user to provide URL |
| Send boundary: "Dang ban tin nay len Telegram giup minh" | v3 | `clarify(response_type=yes_no)` | `transcripts/v3_gemini_20260729T160109179718.transcript.json` | Asked for confirmation instead of sending |

## B5. Tool capability evidence

| Category | Evidence File | What Worked | Risk / Guardrail |
|---|---|---|---|
| Must-have: tool moi dau tien | `tools/source_check/tool.py`, `tools/source_check/TOOL.md`, `runs/v3_B_group_gemini_20260729T155622896451.json` | `source_check` routes and executes in single-turn and multi-turn group cases | Heuristic only, not factual verification |
| Optional built-in | `policy`, `papers`, `paper_text`, `send` declarations remain available | Not claimed as team-new tools | Optional tools can affect routing if descriptions are vague |
| Bonus: tool moi thu 4 tro di | none | Not claimed | Bonus not claimed |

## B6. Reflection

- Fixes in `system_prompt.md`: routing policy, no guessing, missing-info clarification, out-of-scope behavior, send confirmation boundary, concise lookup query convention.
- Fixes in `tools.yaml`: clearer descriptions, argument conventions, `clarify.response_type` required, added `source_check` declaration.
- Manual review needed: provider quota errors in some Gemini runs; those runs are not valid for final metric unless `provider_error_cases=0`.
- Next improvement: build Streamlit UI that reuses `run_model_tool_loop`, shows tool trace, artifact version, and saves transcript.
