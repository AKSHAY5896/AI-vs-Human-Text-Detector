import os
import json
from flask import Flask, render_template, request, jsonify
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

SYSTEM_PROMPT = """You are a forensic text analyst specializing in detecting AI-generated vs human-written content.

Analyze the provided text carefully. Look for:

AI-Generated signals:
- Formulaic transitions ("Furthermore", "Moreover", "It is worth noting")
- Suspiciously comprehensive and balanced coverage of all angles
- Uniform formal register throughout — no tonal shifts
- Absence of personal anecdotes, specific names, or idiosyncratic details
- Over-hedged language ("may", "could", "some argue")
- Perfect paragraph structure without any tangents

Human-Written signals:
- Emotional irregularities and personal voice
- Specific real-world details, names, places
- Inconsistent tone — casual and formal mixed
- Natural imperfections: colloquialisms, incomplete thoughts
- Subjective opinions stated directly without hedging
- Stream-of-consciousness flow or non-linear structure

Respond ONLY with a valid JSON object. No markdown, no backticks, no extra text:
{
  "classification": "AI-Generated" or "Human-Written",
  "confidence": <integer between 55 and 98>,
  "ai_probability": <integer between 0 and 100>,
  "indicators": ["specific observation 1", "specific observation 2", "specific observation 3"],
  "summary": "One precise sentence explaining the verdict"
}"""


def analyze_text(text: str) -> dict:
    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": f"Analyze this text:\n\n{text}"}
        ],
        max_tokens=600,
        temperature=0.1
    )
    response_text = completion.choices[0].message.content.strip()

    # Remove markdown backticks if present
    if "```" in response_text:
        response_text = response_text.split("```")[1]
        if response_text.startswith("json"):
            response_text = response_text[4:]

    return json.loads(response_text.strip())


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    text = data.get("text", "").strip()

    if not text:
        return jsonify({"error": "No text provided."}), 400

    word_count = len(text.split())
    if word_count < 20:
        return jsonify({"error": "Too short — please provide at least 20 words for accurate analysis."}), 400

    if len(text) > 6000:
        return jsonify({"error": "Text too long. Please limit to 6000 characters."}), 400

    try:
        result = analyze_text(text)
        result["classification"] = result.get("classification", "Unknown")
        result["confidence"]     = int(result.get("confidence", 70))
        result["ai_probability"] = int(result.get("ai_probability", 50))
        result["indicators"]     = result.get("indicators", [])[:4]
        result["summary"]        = result.get("summary", "")
        result["word_count"]     = word_count
        return jsonify(result)

    except json.JSONDecodeError:
        return jsonify({"error": "Failed to parse AI response. Please try again."}), 500
    except Exception as e:
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True)