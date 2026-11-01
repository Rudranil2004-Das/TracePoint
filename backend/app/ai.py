import os
import json
from dotenv import load_dotenv

load_dotenv()


def generate_ai_summary(analysis):
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return {
            "available": False,
            "summary": "AI explanation is disabled. "
                       "The statistical analysis was completed locally."
        }

    try:
        from google import genai

        client = genai.Client(api_key=api_key)

        prompt = f"""
You are a professional data analyst.

Review the following dataset analysis and return:
1. A short executive summary.
2. Important findings.
3. Three practical recommendations.
4. Important limitations.

Use clear, professional language.
Do not invent statistics or claim causation from correlation.
Return a JSON object with these keys:
summary, findings, recommendations, limitations.

ANALYSIS:
{json.dumps(analysis, default=str)[:15000]}
"""

        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt
        )

        text = response.text.strip()

        # Remove optional Markdown code fences
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            text = text.rsplit("```", 1)[0]

        result = json.loads(text)
        result["available"] = True
        return result

    except Exception as error:
        return {
            "available": False,
            "summary": "AI explanation could not be generated.",
            "error": str(error)
        }