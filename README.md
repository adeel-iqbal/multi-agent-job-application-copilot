# Multi-Agent Job Application Copilot

A multi-agent AI pipeline built with **LangGraph** and **Chainlit** that takes your resume and a job description as input and produces a tailored cover letter, personalized interview Q&A, and a CV gap report with human-in-the-loop review at every critical step.

---

## What It Does

| Input | Output |
|---|---|
| Your CV (PDF or DOCX) | Tailored Cover Letter |
| Job Description (text) | 12 Interview Q&A (categorized + personalized) |
| | CV Gap Report with severity ratings and advice |
| | Overall match score (out of 10) |

---

## Architecture

### Multi-Agent Pipeline

This project uses a **supervisor-style multi-agent architecture** built on LangGraph's `StateGraph`. Each agent is a specialized node with a single responsibility. All agents share a common state (`AppState`) that persists across the entire pipeline — including across HITL pause points.

```
START
  ↓
[Parser Node]          → reads CV file (PDF/DOCX), extracts raw text
  ↓
[JD Analyzer Agent]    → structured extraction: role, skills, tone, keywords
  ↓
[Cover Letter Agent]   → writes tailored cover letter from JD + CV
  ↓
⏸ HITL 1              → user reviews, approves or requests changes
  ↓ approve            ↓ feedback
[set_final]          [Cover Letter Agent]  ← loops until approved
  ↓
[Interview Prep Agent] → generates 12 Q&A across 4 categories
  ↓
⏸ HITL 2              → user accepts or requests more/focused questions
  ↓ accept             ↓ request
[QA Agent]           [Interview Prep Agent] ← appends new questions
  ↓
[QA Agent]             → gap analysis: identifies missing skills, severity
  ↓
[Assembler Node]       → bundles all outputs into final package
  ↓
END
```

---

## Nodes and Agents

| Node | Type | LLM | Purpose |
|---|---|---|---|
| `parse_cv` | Deterministic | None | Extracts text from PDF/DOCX using PyMuPDF / python-docx |
| `analyze_jd` | LLM Agent | GPT-4o | Structured extraction of role, skills, tone, keywords |
| `write_cover_letter` | LLM Agent | GPT-4o | Writes tailored cover letter, handles regeneration on feedback |
| `hitl_1` | HITL Pause | None | Interrupts graph, waits for user approval or feedback |
| `set_cover_letter_final` | Utility | None | Copies approved draft to final state key |
| `prepare_interview` | LLM Agent | GPT-4o | Generates categorized Q&A, appends on follow-up requests |
| `hitl_2` | HITL Pause | None | Interrupts graph, waits for user acceptance or more questions |
| `run_qa_check` | LLM Agent | GPT-4o | Gap analysis between CV and JD, severity rating, advice |
| `assemble_output` | Deterministic | None | Bundles all outputs into final structured package |

---

## Key Concepts Used

### Shared State
All agents communicate via a single `AppState` TypedDict. No agent calls another directly — they read from and write to shared state. This prevents context loss and keeps the pipeline modular.

### Human-in-the-Loop (HITL)
Two interrupt points using LangGraph's `interrupt_before`:

- **HITL 1** — after cover letter draft. User can approve or give feedback. If feedback given, cover letter agent regenerates with the feedback injected into state. Loop continues until user types `approve`.
- **HITL 2** — after interview Q&A. User can accept or request more/focused questions. New questions are appended to existing ones, not replaced. Loop continues until user types `accept`.

### State Persistence
`MemorySaver` checkpointer stores full pipeline state in memory across HITL pauses. The graph resumes exactly where it left off when the user responds — no data is lost between messages.

### Conditional Edges
Two router functions (`route_after_hitl_1`, `route_after_hitl_2`) read user feedback from state and dynamically route the graph — forward to the next agent or back to the previous one for regeneration.

### Structured Outputs
`JDAnalysis`, `InterviewQAList`, and `GapReport` are Pydantic schemas. LangGraph's `with_structured_output()` enforces typed JSON responses from GPT-4o — no string parsing needed.

### Streaming
Cover letter generation streams token-by-token to the Chainlit UI using `astream_events()` with `on_chat_model_stream` event filtering — only `write_cover_letter` node tokens are streamed.

---

## Interview Q&A Categories

| Category | Count | Description |
|---|---|---|
| Role-specific | 4 | Based on required skills and responsibilities from JD |
| Behavioral | 3 | Based on CV experience, STAR format hints |
| Situational | 3 | Hypothetical scenarios relevant to the role |
| Gap-related | 2 | Questions targeting areas where CV doesn't fully match JD |

---

## Gap Report Severity

| Icon | Severity | Meaning |
|---|---|---|
| 🔴 | Critical | Dealbreaker — must address before interview |
| 🟡 | Moderate | Noticeable gap — prepare an honest response |
| 🟢 | Minor | Nice to have — mention willingness to learn |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Agent Orchestration | LangGraph |
| LLM | OpenAI GPT-4o |
| UI | Chainlit |
| PDF Parsing | PyMuPDF (fitz) |
| DOCX Parsing | python-docx |
| Structured Output | Pydantic v2 |
| State Persistence | LangGraph MemorySaver |
| Environment | python-dotenv |

---

## Project Structure

```
multi-agent-job-application-copilot/
│
├── graph/
│   ├── __init__.py
│   ├── state.py                  # AppState TypedDict — shared pipeline state
│   ├── graph.py                  # StateGraph definition, edges, HITL, routers
│   └── nodes/
│       ├── __init__.py
│       ├── parser.py             # CV file parser (PDF + DOCX)
│       ├── jd_analyzer.py        # JD structured extraction agent
│       ├── cover_letter.py       # Cover letter generation agent
│       ├── interview_prep.py     # Interview Q&A generation agent
│       ├── qa_agent.py           # Gap analysis agent
│       └── assembler.py          # Final output assembler
│
├── public/
│   ├── theme.json                # Chainlit dark + purple theme
│   └── custom.css                # Custom UI styling
│
├── .chainlit/
│   └── config.toml               # Chainlit app configuration
│
├── shots/                        # Screenshots
│   ├── 1.png
│   ├── 2.png
│   ├── 3.png
│   ├── 4.png
│   ├── 5.png
│   ├── 6.png
│   ├── 7.png
│   ├── 8.png
│   └── 9.png
│
├── app.py                        # Chainlit entry point
├── requirements.txt
├── .env                          # API keys (not committed)
└── .gitignore
```

---

## Screenshots

| | | |
|---|---|---|
| ![1](shots/1.png) | ![2](shots/2.png) | ![3](shots/3.png) |
| ![4](shots/4.png) | ![5](shots/5.png) | ![6](shots/6.png) |
| ![7](shots/7.png) | ![8](shots/8.png) | ![9](shots/9.png) |

---

## Setup and Installation

**1. Clone the repository**
```bash
git clone https://github.com/adeel-iqbal/multi-agent-job-application-copilot.git
cd multi-agent-job-application-copilot
```

**2. Create and activate virtual environment**
```bash
python -m venv venv
venv\Scripts\Activate        # Windows
source venv/bin/activate     # Mac/Linux
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Add your OpenAI API key**

Create a `.env` file in the root:
```
OPENAI_API_KEY=your_openai_api_key_here
```

**5. Run the app**
```bash
chainlit run app.py
```

Open `http://localhost:8000` in your browser.

---

## How to Use

1. Open the app in your browser
2. Upload your **CV** (PDF or DOCX) using the attachment button
3. Paste the **Job Description** text in the message input
4. Send both together
5. Review the streaming cover letter draft
6. Type `approve` to continue or give feedback to rewrite
7. Review the 12 interview questions
8. Type `accept` to finalize or request more questions
9. Receive your complete application package

---

## Requirements

```
langgraph
langchain-openai
langchain-core
chainlit
python-docx
pymupdf
python-dotenv
pydantic
```

---

## Author

**Adeel Iqbal**

- Email: adeelmemon096@yahoo.com
- LinkedIn: [linkedin.com/in/adeeliqbalmemon](https://linkedin.com/in/adeeliqbalmemon)
- GitHub: [github.com/adeel-iqbal](https://github.com/adeel-iqbal/multi-agent-job-application-copilot.git)

---

## License

MIT License — free to use, modify, and distribute.
