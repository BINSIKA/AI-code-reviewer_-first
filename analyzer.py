"""
Module 3: ai_suggester.py
AI-powered code analysis using Groq + LLaMA 3.1.
Provides summary, corrected code, and optimization suggestions.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────
#  Groq LLaMA via LangChain
# ─────────────────────────────────────────

class AISuggester:
    """
    Wraps Groq's LLaMA model to generate code review reports.
    """

    MODEL = "llama-3.1-8b-instant"

    def __init__(self):
        try:
            from langchain_groq import ChatGroq
            self.llm = ChatGroq(
                model=self.MODEL,
                api_key=os.getenv("GROQ_API_KEY"),
                temperature=0.2,
                max_tokens=1500,
            )
            self.available = True
        except Exception as e:
            self.llm = None
            self.available = False
            self._error = str(e)

    # ── Main review ──────────────────────────────────────────────

    def generate_report(
        self,
        code: str,
        language: str,
        static_issues: list[str],
    ) -> dict:
        """
        Generate a full AI review report.

        Returns dict with keys:
            summary, corrected_code, optimizations, raw
        """
        if not self.available:
            return self._fallback_report(code, language)

        issues_text = (
            "\n".join(f"  - {i}" for i in static_issues)
            if static_issues else "  None detected."
        )

        prompt = f"""You are an expert {language} Teacher and Code Reviewer.

Review the following {language} code carefully:

```{language}
{code}
```

Static Analysis already found these issues:
{issues_text}

Respond ONLY with a valid JSON object (no markdown, no preamble) in this exact shape:
{{
  "summary": "2-3 sentences describing what the code does and its overall quality",
  "corrected_code": "the complete corrected version of the code with all bugs fixed",
  "optimizations": [
    "Optimization tip 1",
    "Optimization tip 2",
    "Optimization tip 3"
  ],
  "detected_bugs": [
    "Bug description with line reference if possible"
  ]
}}"""

        try:
            response = self.llm.invoke(prompt)
            raw = response.content.strip()

            # Strip markdown code fences if present
            raw = raw.replace("```json", "").replace("```", "").strip()

            import json
            data = json.loads(raw)
            data["raw"] = raw
            return data

        except Exception as e:
            return {
                "summary": f"AI analysis failed: {str(e)}",
                "corrected_code": code,
                "optimizations": ["Could not generate optimizations — check API key."],
                "detected_bugs": [],
                "raw": str(e),
            }

    # ── Chat message ─────────────────────────────────────────────

    def chat_message(
        self,
        user_message: str,
        context: str = "",
        history: list[dict] = None,
    ) -> str:
        """
        Answer a follow-up question about the code analysis.

        Args:
            user_message: User's question.
            context:      Latest analysis context string.
            history:      List of {"role": ..., "content": ...} dicts.

        Returns:
            AI reply string.
        """
        if not self.available:
            return "⚠️ AI unavailable — check your GROQ_API_KEY in .env"

        system = (
            "You are an expert AI code reviewer assistant. "
            "Help users understand their code analysis results, "
            "fix bugs, and improve code quality. Be concise and practical."
        )
        if context:
            system += f"\n\nLatest analysis context:\n{context}"

        messages = [("system", system)]
        if history:
            for h in history[-8:]:  # keep last 8 turns
                messages.append((h["role"], h["content"]))
        messages.append(("human", user_message))

        try:
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            return f"⚠️ AI Error: {str(e)}"

    # ── Fallback ─────────────────────────────────────────────────

    def _fallback_report(self, code: str, language: str) -> dict:
        lines = code.strip().split('\n')
        return {
            "summary": (
                f"This is a {language} code snippet with {len(lines)} lines. "
                "AI analysis is unavailable — please set your GROQ_API_KEY in the .env file."
            ),
            "corrected_code": code,
            "optimizations": [
                "Set GROQ_API_KEY in .env to enable AI suggestions.",
                "Review the static analysis results above for detected issues.",
                "Consider using a linter specific to your language.",
            ],
            "detected_bugs": [],
            "raw": "AI unavailable",
        }
