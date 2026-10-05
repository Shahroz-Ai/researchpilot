# 🧭 ResearchPilot - AI Research Agent

> An AI agent that decides for itself how to research a question: it searches
> the web, reads pages, does math, and writes a sourced report. 🔍

🔗 **Live demo:** https://researchpilot-shahroz.streamlit.app/

---

## 🎯 What is this?

ResearchPilot is an **autonomous research agent**. You ask a question, and the
AI chooses its own steps: which tool to use, what to search for, which page to
read, and when it has enough evidence to stop. Then it writes a structured
report with sources.

Unlike a normal chatbot, it does not answer from memory. It goes and checks. ✅

## ✨ Features

- 🤖 **Real agent loop**: the model picks the tools and decides when to stop
- 🔍 **Web search** using DuckDuckGo (no API key needed)
- 📖 **Page reader with pagination**: reads long pages chunk by chunk
- 🧮 **Safe calculator**: built on Python's `ast` module, no `eval`, so no code injection
- 📋 **Live progress**: every agent step is shown in the UI as it happens
- 🛡️ **Safety limits**: step limit, repeat-call detection, and retry with model fallback
- 🚫 **Grounded reports**: facts that are not in the sources are marked "not found"
- ⬇️ **Download**: save any report as a Markdown file

## ⚙️ How it works

```
Question
   │
   ▼
┌──────────────────────────────┐
│  Agent loop (max 8 steps)    │
│  1. Model chooses a tool     │
│  2. App runs the tool        │
│  3. Result goes back to model│
│  4. Repeat until enough info │
└──────────────────────────────┘
   │
   ▼
Research notes ──► Report writer ──► Sourced report
```

1. 🧠 The model receives the question and 3 tools
2. 🔧 It asks for a tool, the app runs it, and the result goes back to the model
3. 🔁 This repeats until the model has enough evidence (maximum 8 steps)
4. 📝 A separate prompt writes the final report using **only the collected notes**
5. 🧹 The report is cleaned (citation formats) before it is shown

The agent loop is written **from scratch, without LangChain**, to keep the logic
simple and transparent.

## 🧰 The tools

| Tool | What it does |
|------|--------------|
| 🔍 `web_search` | Searches the web and returns titles, links, and snippets |
| 📖 `read_page` | Reads a web page about 4000 characters at a time, with a `start` offset for the next part |
| 🧮 `calculator` | Evaluates math expressions safely |

## 🛡️ Reliability and safety

- 🔁 **Repeat detection**: if the agent repeats the same call, it is told to change its approach, and after 3 repeats it is stopped
- 🔄 **Model fallback**: if one model fails or is busy, the next one is tried automatically
- ⏱️ **Retry with backoff** for temporary API errors
- 🧱 **Step limit** so the agent can never loop forever
- 🔒 **Sandboxed calculator**: only numbers and basic operators are allowed
- 🙅 **Anti-hallucination prompt**: the report writer must say "not found in sources" instead of guessing

## 🛠️ Tech stack

| Area | Tools |
|------|-------|
| 🐍 Language | Python |
| 🎨 UI | Streamlit |
| 🤖 LLM | Groq API (tool calling) |
| 🔍 Search | ddgs (DuckDuckGo) |
| 📄 Page extraction | trafilatura |

## 📁 Project structure

```
researchpilot/
├── app.py            # Streamlit UI with live agent steps
├── agent.py          # Agent loop, prompts, retry and fallback logic
├── tools.py          # Search, page reader, calculator, and tool schemas
├── requirements.txt  # Dependencies
└── .gitignore
```

## 🚀 Run locally

1. Clone the repo and install dependencies:
```
   pip install -r requirements.txt
```
2. Create a `.env` file in the project folder and add your key: 🔑
```
   GROQ_API_KEY=your_key_here
```
3. Start the app:
```
   python -m streamlit run app.py
```

You can also test the agent in the terminal with `python agent.py`.

## 💡 Example questions

- 🏍️ Compare the top 3 electric bike brands in Pakistan and give their price range.
- 🐍 What is the latest stable version of Python and when was it released?
- 💰 If a laptop costs 85000 PKR and gets a 12% discount, what is the final price?

## ⚠️ Limitations

- 🌐 Report quality depends on what web search returns
- 📚 The agent often relies on one or two sources per question
- 🔢 Numbers should be double-checked against the cited source
- ⏳ Free API limits apply, so the demo allows 5 questions per session
- 🚫 No login or personal data is stored

## 🗺️ Roadmap

- [ ] Compare several sources automatically and flag disagreements
- [ ] Add a second search provider as a fallback
- [ ] Chat memory for follow-up questions
- [ ] Export reports as PDF
- [ ] Evaluation set to measure answer accuracy

---

Made with ❤️ by **Shahroz**
