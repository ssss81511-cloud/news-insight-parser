# News Insight Agent

## Purpose
Agent for parsing news sources and identifying insights, patterns, and emerging signals in the SaaS/startup ecosystem.

---

## Data Sources

Analyze content ONLY from:

1. **Indie Hackers** – discussions and comments
2. **Hacker News** – "new" and "ask" sections
3. **Product Hunt** – new launches and comments
4. **Reddit** – 2–3 SaaS-related subreddits
5. **VC blogs** – 1–2 venture funds (strategic thinking, not PR)

---

## Signals to Extract

### 1. Repeating Pains
- Founders complaining about the same problem across sources
- Operational, growth, pricing, infra, or customer-related pain
- Track frequency and context

### 2. Unusual or Emerging Language
- New terms, metaphors, or phrases
- Shifts in wording (e.g. "freemium" → "usage-based")
- Language evolution patterns

### 3. New Solution Patterns
- Similar workarounds appearing independently
- Multiple founders building near-identical tools
- Convergent problem-solving approaches

### 4. Behavioral Patterns
- Use sequential thinking
- Track decision-making patterns
- Identify behavioral shifts in founder/user actions

---

## Analysis Methodology

1. **Collection Phase**
   - Scrape/parse designated sources
   - Normalize data format
   - Timestamp and tag by source

2. **Pattern Detection**
   - Cross-reference similar complaints/solutions
   - Identify frequency thresholds
   - Map language evolution

3. **Insight Generation**
   - Cluster related signals
   - Rank by strength/frequency
   - Generate actionable insights

4. **Output Format**
   - Structured reports
   - Trend visualizations
   - Alert on emerging patterns

---

## Implementation Notes

- Respect rate limits and ToS for each source
- Implement caching to avoid redundant requests
- Use NLP for pattern matching and clustering
- Store results in structured format (JSON/DB)
