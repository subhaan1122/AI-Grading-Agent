## 🧠 AI Grading Agent

An intelligent grading assistant powered by AI to automate answer checking for subjective, descriptive, and theoretical questions. 
This project allows educators, tutors, or interviewers to evaluate candidate responses against an ideal answer and grading rubric — using natural language understanding.

## 🚀 Features

- 📥 Upload both question + ideal answer and student answer
- 🔍 Evaluates on:
    1- Keyword & Concept Match
    2- Coherence
    3- Language Fluency
    4- Semantic Similarity
- 💯 Generates a Score (out of 10) with reasoning
- 🧠 Powered by Google Gemini (Generative AI)
- 🖥️ Interactive Streamlit web app for easy grading

## 🧠 Tech Stack

| Component       | Technology                             |
| --------------- | -------------------------------------- |
| Frontend UI     | Streamlit                              |
| LLM Backend     | Gemini Pro (via `google.generativeai`) |
| File Processing | Python (TXT, DOCX, PDF)                |
| Grading Logic   | Prompt Engineering + NLP               |
| Others          | `pdfplumber`, `docx`, `datetime`       |

---

## 📂 Folder Structure

```
AI Grading Agent/
├── app.py                 # Streamlit UI
├── grading_logic.py       # Gemini prompts & grading engine
├── utils.py               # File parsers & helpers
├── requirements.txt       # All dependencies
```

---

## 🎓 Example Use Case

**Upload Inputs:**

1. 🟢 *Ideal Answer + Question*
2. 🔵 *Student Response*

**Output:**

* ✅ Score: `7.5/10`
* 💡 Reasoning:

  * Missed 2 key points
  * Lacks conclusion
  * Good language fluency
  * Average structure

---

## 📦 How to Run Locally

```bash
git clone https://github.com/yourusername/ai-grading-agent.git
cd ai-grading-agent
pip install -r requirements.txt
streamlit run app.py
```

**Note**: Replace your `Gemini API Key` inside the code or `.env` file.

---
