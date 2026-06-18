import os
import json
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

VALID_SEVERITIES = {"BROKEN", "POTENTIALLY_OUTDATED", "REVIEW_RECOMMENDED", "SAFE"}


class LLMService:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = "llama-3.3-70b-versatile"

    def generate_documentation(self, code_snippet):
        prompt = f"""
        You are an expert technical writer. Generate comprehensive Markdown documentation for the following code.
        Include: Purpose, Parameters, Return values, Side effects, Usage examples, and Edge cases.

        CODE:
        {code_snippet}
        """
        response = self.client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=self.model,
        )
        return response.choices[0].message.content

    def detect_staleness_and_draft(self, old_doc: str, patch: str) -> dict:
        prompt = f"""You are a technical documentation reviewer.

Analyze the Git patch below against the existing documentation and return ONLY a JSON object — no extra text, no markdown fences.

PATCH:
{patch}

EXISTING DOCUMENTATION:
{old_doc}

Return this exact JSON structure:
{{
  "severity": "<one of: BROKEN | POTENTIALLY_OUTDATED | REVIEW_RECOMMENDED | SAFE>",
  "reasoning": "<one or two sentences explaining why the docs are or are not stale>",
  "updated_doc": "<full updated Markdown documentation, or the original if severity is SAFE>"
}}

Rules:
- BROKEN: The patch changes or removes something directly documented (signatures, return types, endpoints).
- POTENTIALLY_OUTDATED: The patch likely affects documented behaviour but not definitively.
- REVIEW_RECOMMENDED: Minor changes that may or may not affect docs.
- SAFE: No documented behaviour was changed.
- updated_doc must always be valid Markdown.
- Respond with ONLY the JSON object."""

        response = self.client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=self.model,
        )
        raw = response.choices[0].message.content
        return self._parse_json_response(raw, old_doc)

    def _parse_json_response(self, raw: str, old_doc: str) -> dict:
        # Strip markdown code fences if present
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)

        try:
            data = json.loads(cleaned)
            # Normalise severity to uppercase and validate
            severity = str(data.get("severity", "REVIEW_RECOMMENDED")).upper().strip()
            if severity not in VALID_SEVERITIES:
                severity = "REVIEW_RECOMMENDED"
            return {
                "severity": severity,
                "reasoning": str(data.get("reasoning", "")),
                "updated_doc": str(data.get("updated_doc", old_doc)),
            }
        except json.JSONDecodeError:
            return {
                "severity": "REVIEW_RECOMMENDED",
                "reasoning": "LLM returned non-JSON output; manual review required.",
                "updated_doc": old_doc,
            }

    def chat_with_context(self, question, context):
        prompt = f"""
        Answer the developer's question using ONLY the provided documentation context. 
        If the answer is not in the context, say "I cannot find this in the documentation." Do not hallucinate.
        
        CONTEXT:
        {context}
        
        QUESTION: {question}
        """
        response = self.client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=self.model,
        )
        return response.choices[0].message.content