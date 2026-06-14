- This workspace is for periodic, user-initiated stock/company analysis, not automated trading.
- Treat outputs as evidence-based decision support, not guaranteed investment advice.
- For stock, ETF, company, price-move, earnings, or valuation questions, verify recent data with web research before giving a current judgment.
- Prefer primary sources first: SEC filings, DART filings, IR reports, earnings releases, exchange data, central bank data. Use news only as context after checking primary facts.
- Always state the base date in Seoul time for current market data.
- Default operating loop for substantive investment questions:
  1. Build a question context pack with `uv run python scripts/build_context_pack.py "<question>"` when the request names or implies a security.
  2. Refresh or prepare evidence with `uv run python scripts/update_asset_bundle.py <SYMBOL> --market US|KR --asset-type stock|ETF` when a relevant local path exists.
  3. For portfolio-aware answers, compute current exposure with `uv run python scripts/portfolio_snapshot.py` after supplying fresh prices/FX when available.
  4. Use the routed project-owned skill for analysis, then let `risk-manager-investment-memo` control the final action label.
- For portfolio-aware questions, read `companies/portfolio_profile.yaml`, `companies/holdings.yaml`, and `companies/watchlist.yaml` before asking the user for position context.
- Do not ask the user to repeat portfolio facts already recorded in those files unless the data is stale, missing, or internally conflicting.
- Treat `companies/holdings.yaml` as the user-maintained source of truth for ticker, market, account, asset type, shares, average price, currency, and thesis. Compute current value, P/L, and portfolio weights on demand from fresh market data.
- Do not change recorded shares or average price unless the user explicitly reports a buy, sell, transfer, split adjustment, or correction.
- Treat recorded portfolio files as user-provided context, not live market data. Still verify recent prices, filings, issuer data, and disclosures before current buy/hold/trim/avoid judgments.
- Keep analysis balanced and risk-aware: downside control, valuation heat checks, cash as a valid position, no leverage by default, and no averaging down unless the original thesis still holds.
- Prefer the local `uv run python scripts/...` pipeline before ad hoc analysis when a relevant fetch/normalize script exists.
- Treat this repo's local scripts and project-owned skills as the primary investment decision workflow. Use external plugins only as supplemental research, artifact, model, or QC layers unless the user explicitly asks for that plugin's workflow.
- Public Equity Investing plugin scope:
  - Inline answer by default for ordinary buy/hold/trim/avoid, news, valuation, or portfolio questions in this repo. Use PEI HTML/XLSX artifacts only when the user asks for a formal artifact, model, tracker, pitch, scenario package, or QC pass.
  - Use it for institutional-style public-equity artifacts such as source-backed company tearsheets, initiating coverage, earnings previews/deep dives, comps, DCF/3-statement workbooks, model updates, long/short pitches, thesis trackers, catalyst calendars, portfolio-risk screens, meeting prep, and deck/model QC.
  - Do not use it to replace local fetch/normalize scripts, portfolio files, project-owned US/KR/ETF routing, final action labels, position sizing rules, or risk controls.
  - When its source categories or connectors are unavailable, continue only from local artifacts, user-provided files, primary public sources, web research, or explicitly labeled assumptions. Mark unsupported consensus, ownership, borrow, liquidity, options, internal-research, or model fields as missing/preliminary rather than inventing them.
  - For Korean equities and Korea-listed ETFs, use local DART/KRX/KIND/issuer workflows first; use the plugin only for report structure, valuation framing, scenario work, or polished artifacts after Korea-specific evidence is gathered.
- For ETF judgment, comparison, price-move, holdings, NAV, expense, tracking, dividend/yield, leveraged ETF, or inverse ETF questions, use `etf-analysis-review`; do not force ETF questions through company financial-statement workflows.
- For US stock judgment, use project-owned `us-stock-decision-workflow` first; treat external `us-stock-analysis` only as a supplemental checklist.
- Default investment workflow is evidence-first risk/reward assessment.
- For return-seeking US stock analysis, use `us-stock-return-opportunity` when the user explicitly asks for upside, growth, momentum, alpha, aggressive opportunity, rerating, or catalyst-driven buying.
- If the user request is ambiguous, present both lenses briefly: risk-management verdict and return-opportunity verdict. The risk-management verdict controls the final action label.
- External `us-stock-analysis` remains a supplemental checklist only; it must not override project labels, source hierarchy, position sizing, or risk controls.
- For Korean stock judgment, use `kr-stock-analysis-review`; do not force US-market assumptions onto DART/KRX analysis.
- Keep project-only skills under `.agents/skills/`; external reusable skills should come from `npx skills` global installs.
- Treat `companies/thesis_tracker.yaml` as the local lightweight thesis/catalyst/action-log scaffold. Append new thesis events there or in a dated memo only when the user asks to persist/update tracking state.
- Store raw fetched data under `data/raw/`, normalized financial data under `data/normalized/`, generated analysis bundles under `data/reports/`, and final human-readable investment notes under `memos/`.
