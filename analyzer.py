import anthropic
import json
import streamlit as st


def get_client():
    api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
    return anthropic.Anthropic(api_key=api_key)


def analyze_strategy(brand_name, industry, brand_description, target_market, deck_content, deck_name):
    client = get_client()

    prompt = f"""You are a senior business strategy consultant with deep expertise across all industries. Analyze the strategy document below and evaluate its effectiveness for "{brand_name}".

**Brand Profile:**
- Brand: {brand_name}
- Industry: {industry}
- Description: {brand_description or "Not provided"}
- Target Market: {target_market or "Not provided"}
- Document: {deck_name}

**Strategy Document:**
{deck_content[:15000]}

**Instructions:** Score this strategy across 8 dimensions. Be specific, honest, and actionable. Factor in the industry context when scoring.

Return ONLY a valid JSON object — no markdown, no explanation, just the JSON:
{{
  "overall_score": <integer 0-100>,
  "executive_summary": "<2-3 sentences on overall effectiveness>",
  "verdict": "<Highly Effective | Effective | Needs Improvement | Ineffective>",
  "dimensions": {{
    "clarity": {{
      "score": <0-100>,
      "label": "Clarity",
      "feedback": "<2-3 sentences of specific feedback>",
      "strengths": ["<strength>", "<strength>"],
      "improvements": ["<improvement>", "<improvement>"]
    }},
    "target_audience": {{
      "score": <0-100>,
      "label": "Target Audience",
      "feedback": "<2-3 sentences>",
      "strengths": ["<strength>"],
      "improvements": ["<improvement>"]
    }},
    "competitive_advantage": {{
      "score": <0-100>,
      "label": "Competitive Advantage",
      "feedback": "<2-3 sentences>",
      "strengths": ["<strength>"],
      "improvements": ["<improvement>"]
    }},
    "feasibility": {{
      "score": <0-100>,
      "label": "Feasibility",
      "feedback": "<2-3 sentences>",
      "strengths": ["<strength>"],
      "improvements": ["<improvement>"]
    }},
    "risk_assessment": {{
      "score": <0-100>,
      "label": "Risk Assessment",
      "feedback": "<2-3 sentences>",
      "strengths": ["<strength>"],
      "improvements": ["<improvement>"]
    }},
    "kpis_metrics": {{
      "score": <0-100>,
      "label": "KPIs & Metrics",
      "feedback": "<2-3 sentences>",
      "strengths": ["<strength>"],
      "improvements": ["<improvement>"]
    }},
    "market_alignment": {{
      "score": <0-100>,
      "label": "Market Alignment",
      "feedback": "<2-3 sentences>",
      "strengths": ["<strength>"],
      "improvements": ["<improvement>"]
    }},
    "brand_consistency": {{
      "score": <0-100>,
      "label": "Brand Consistency",
      "feedback": "<2-3 sentences>",
      "strengths": ["<strength>"],
      "improvements": ["<improvement>"]
    }}
  }},
  "top_strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
  "critical_risks": ["<risk 1>", "<risk 2>", "<risk 3>"],
  "recommendations": [
    {{"priority": "High", "action": "<specific actionable step>"}},
    {{"priority": "High", "action": "<specific actionable step>"}},
    {{"priority": "Medium", "action": "<specific actionable step>"}},
    {{"priority": "Medium", "action": "<specific actionable step>"}},
    {{"priority": "Low", "action": "<specific actionable step>"}}
  ]
}}"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text.strip()

    # Strip markdown code fences if present
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        response_text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

    return json.loads(response_text)
