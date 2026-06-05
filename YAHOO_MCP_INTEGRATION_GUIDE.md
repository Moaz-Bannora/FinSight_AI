# Yahoo Finance MCP Integration Guide

This guide explains how a Yahoo Finance MCP integration can fit into Finance Docs Insights without weakening the existing local RAG project.

The short version: Yahoo MCP should be an optional read-only market-data layer. It should not replace document RAG. Uploaded documents and sample docs remain the evidence base for filings, forms, reports, and course concepts. Yahoo MCP can add current or historical market context when the user explicitly asks for ticker, quote, price-history, news, options, or market-comparison information.

## Why It Is Useful

Finance Docs Insights currently answers from:

- Uploaded documents
- Built-in sample finance notes
- Exported financial-doc chunks
- Deterministic finance calculators
- Optional Gemini vision summaries

That is strong for document understanding, but it does not provide live market context. A Yahoo Finance MCP layer can help with questions like:

```text
Compare the risk section in this uploaded Tesla filing with recent TSLA market movement.
What is Apple's current market cap, then explain how it relates to valuation ratios?
Show Microsoft one-year price trend and connect it to the uploaded report's revenue discussion.
Summarize recent news for NVDA and separate market data from document evidence.
```

Useful data types:

- Current quote and market cap
- Price history
- Volume and volatility context
- Dividend and split history
- Earnings dates
- Analyst recommendations
- Options chain summary
- Recent company news
- Search for ticker symbols

## Important Boundary

Yahoo MCP data is external market data. It should be displayed and reasoned about separately from retrieved document evidence.

Recommended answer sections:

```text
Direct Answer
Document Evidence
Market Data Context
Calculation or Interpretation
Limitations
```

Do not blend Yahoo data into the same section as uploaded PDF evidence. This keeps citations honest and makes the system easier to defend during the course presentation.

## MCP Fit In The Architecture

Official MCP documentation describes servers as exposing tools, resources, and prompts to clients. For this project, Yahoo Finance should be exposed as tools, because the model should call it only when the question needs live or historical market data.

Recommended architecture:

```text
User question
  -> FinanceAssistant
     -> Safety check
     -> Query router
        -> Document RAG when file/document evidence is needed
        -> Finance calculators when arithmetic is needed
        -> Yahoo MCP tools when market data is needed
     -> Researcher answer
     -> Checker validation
     -> UI renders sources and tool outputs separately
```

The MCP layer should be behind a local adapter, not called directly from prompts. That adapter gives the project one clean place to enforce safety, caching, timeouts, and output formatting.

## Recommended Implementation Path

### Phase 1: Direct Local Market Data Adapter

Start with a small internal adapter before adding full MCP client complexity:

```text
src/market_data.py
```

Suggested functions:

- `get_quote(symbol: str) -> MarketQuote`
- `get_price_history(symbol: str, period: str, interval: str) -> PriceHistory`
- `get_company_summary(symbol: str) -> CompanySummary`
- `get_recent_news(symbol: str, limit: int = 5) -> list[NewsItem]`

This can use `yfinance` or a selected Yahoo Finance MCP server internally, but the assistant should receive normalized project-owned objects.

Why start here:

- Easier to test.
- No extra process management in Streamlit.
- Easier to keep read-only.
- Easier to add caching and rate-limit protection.

### Phase 2: MCP Server Option

Add optional MCP support after the adapter is stable.

Possible community servers to evaluate:

- `AgentX-ai/yahoo-finance-server`: exposes ticker data, news, search, price history, options, earnings, and related Yahoo Finance features.
- `barvhaim/yfinance-mcp-server`: exposes real-time stock information, historical data, financial statements, earnings, dividends/splits, news, recommendations, and search.

Evaluation checklist:

- Is the project maintained?
- Does it use a permissive license?
- Does it require API keys or scraping?
- Does it return structured JSON?
- Does it handle rate limits cleanly?
- Does it expose only read-only tools?
- Can it run locally on Windows?
- Can it be pinned to a specific version?

### Phase 3: Tool Router

Add a controlled routing layer:

```text
src/tool_router.py
```

The router decides:

- Use RAG for uploaded report, form, PDF, source, page, section, filing, document, evidence.
- Use finance calculators for ratio, NPV, WACC, ROE, margin, duration, convexity, VaR, CVaR.
- Use Yahoo market data for ticker, stock price, market cap, option chain, dividend, split, historical price, recent news.

This avoids making the LLM guess which tool to call.

### Phase 4: UI Option

Add one small sidebar toggle:

```text
Use live market data
```

Default: off.

Only show it under `4. Runtime options and status`, so the app does not become crowded.

When off, the app should still answer document and concept questions exactly as it does now.

## Security And Safety Rules

Yahoo MCP must be read-only.

Do:

- Cache results for a short time to avoid repeated calls.
- Log ticker, tool name, latency, and status.
- Time out quickly and fall back gracefully.
- Show market data as external context.
- Keep educational disclaimers for investment decisions.
- Validate ticker symbols and prevent arbitrary URLs.

Do not:

- Allow trading, order placement, portfolio actions, or brokerage connections.
- Treat Yahoo data as guaranteed accurate.
- Use live market data to give personalized buy/sell advice.
- Let MCP tool descriptions override system prompts.
- Pass private uploaded documents into an external MCP server.

## Example Prompt Contract

Market-data tool output should be summarized like this:

```text
MARKET DATA CONTEXT:
Provider: Yahoo Finance via local MCP adapter
Ticker: AAPL
As of: 2026-06-05 19:45 UTC
Fields:
- price: ...
- market_cap: ...
- 52_week_range: ...
- recent_news_titles: ...

Rules:
- Treat this as external market data, not uploaded document evidence.
- Do not give personalized investment advice.
- Mention stale/missing fields if present.
```

## How It Improves Answers

Without Yahoo MCP:

- The assistant can explain valuation concepts from documents.
- It cannot reliably know current price, market cap, or recent news.

With Yahoo MCP:

- The assistant can compare document fundamentals with recent market context.
- It can calculate educational ratios using a current market price when the user asks.
- It can separate "what the filing says" from "what the market currently shows."

This is especially useful for company health analysis, valuation study questions, and research-style prompts.

## Risks

- Yahoo Finance and yfinance are not official guaranteed enterprise feeds.
- Community MCP servers may change, disappear, or have security issues.
- Live data can make answers slower and harder to reproduce.
- Free sources can be rate-limited.
- Market context may tempt the model into advice, so safety checks must stay active.

For the course project, the safest version is a small read-only adapter with a UI toggle and clear output labeling. Full MCP support can be presented as an extension path.

## Suggested Files For A Future Implementation

```text
src/market_data.py              normalized market-data adapter
src/tool_router.py              routes RAG, calculators, image analysis, market data
tests/test_market_data_router.py
tests/test_market_data_safety.py
requirements-market-data.txt    optional yfinance/MCP dependencies
```

## References

- Model Context Protocol architecture: https://modelcontextprotocol.io/docs/learn/architecture
- Model Context Protocol SDKs: https://modelcontextprotocol.io/docs/sdk
- Model Context Protocol security best practices: https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices
- yfinance documentation: https://ranaroussi.github.io/yfinance/
- AgentX Yahoo Finance MCP server: https://github.com/AgentX-ai/yahoo-finance-server
- yfinance MCP server example: https://github.com/barvhaim/yfinance-mcp-server
