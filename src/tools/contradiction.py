from __future__ import annotations

from src.tools.base import BaseTool


class ContradictionChecker(BaseTool):
    @property
    def name(self) -> str:
        return "contradiction_checker"

    @property
    def description(self) -> str:
        return "Detect logical contradictions, overgeneralizations, and unsupported absolute claims in text."

    def _parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to analyze for contradictions and fallacies.",
                }
            },
            "required": ["text"],
        }

    async def run(self, **kwargs) -> dict:
        text = kwargs.get("text", "")
        issues: list[str] = []

        absolutes = ["always", "never", "everyone", "nobody", "all", "none", "impossible"]
        text_lower = text.lower()
        for word in absolutes:
            if word in text_lower:
                issues.append(f"Potential overgeneralization: '{word}' detected — claims with absolute language often lack nuance.")

        if "prove" in text_lower and ("obvious" in text_lower or "clear" in text_lower):
            issues.append("Circular reasoning indicator: claiming something is 'obvious' or 'clear' without providing evidence.")

        if issues:
            return {"found": True, "issues": issues}
        return {"found": False, "issues": []}
