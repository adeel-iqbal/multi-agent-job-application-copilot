# qa_agent.py — compares CV against JD and finds skill/experience gaps
# gives user an honest picture of weak spots before the interview
# no fabrication — only flags what's genuinely missing or weak

import os                                                    # for env variables
from dotenv import load_dotenv                               # load .env file
from langchain_openai import ChatOpenAI                      # OpenAI LLM
from langchain_core.messages import SystemMessage, HumanMessage  # message types
from pydantic import BaseModel, Field                        # structured output
from typing import List                                      # typed list
from graph.state import AppState                             # shared state

# load environment variables from .env
load_dotenv()


# --- Structured Output Schema ---

class GapItem(BaseModel):
    """A single identified gap between CV and JD"""

    # the specific skill or experience that is missing or weak
    gap: str = Field(description="The specific skill or experience gap identified")

    # severity helps user prioritize what to address
    severity: str = Field(description="Severity level: critical, moderate, or minor")

    # actionable advice on how to address this gap
    advice: str = Field(description="Specific advice on how to address or handle this gap")


class GapReport(BaseModel):
    """Full gap report comparing CV against JD requirements"""

    # list of all identified gaps
    gaps: List[GapItem] = Field(description="List of identified gaps between CV and JD")

    # overall match score out of 10
    match_score: int = Field(description="Overall match score between CV and JD out of 10")

    # one line overall assessment
    overall_assessment: str = Field(description="One sentence overall assessment of the application strength")


def run_qa_check(state: AppState) -> dict:
    """
    QA Agent node — performs gap analysis between CV and JD.
    Uses jd_analysis + cv_raw_text from state.
    Writes result into state['qa_flags'].
    """

    # initialize OpenAI LLM
    llm = ChatOpenAI(
        model="gpt-4o",                         # latest capable model
        temperature=0,                          # 0 = deterministic gap analysis
        api_key=os.getenv("OPENAI_API_KEY")     # key from .env
    )

    # bind structured output schema
    structured_llm = llm.with_structured_output(GapReport)

    # pull what we need from shared state
    jd_analysis = state.get("jd_analysis", {})
    cv_raw_text = state.get("cv_raw_text", "")

    # extract from jd_analysis for cleaner prompt
    role = jd_analysis.get("role", "the role")
    required_skills = jd_analysis.get("required_skills", [])
    responsibilities = jd_analysis.get("responsibilities", [])
    experience_level = jd_analysis.get("experience_level", "")
    keywords = jd_analysis.get("keywords", [])

    # system prompt — strict honest gap analysis rules
    system_prompt = SystemMessage(content="""
        You are a brutally honest but constructive career advisor.
        Your job is to compare a CV against job requirements and identify gaps.

        Rules:
        - Only flag gaps that are genuinely missing or weak in the CV
        - Do NOT fabricate gaps that don't exist
        - Be specific — name the exact skill or experience missing
        - Severity: critical = dealbreaker, moderate = noticeable, minor = nice to have
        - Advice must be actionable and interview-focused
        - Match score: 10 = perfect match, 1 = very poor match
        - Be honest but constructive — this helps the applicant prepare
    """)

    # human message — passes full context for comparison
    human_message = HumanMessage(content=f"""
        Compare this applicant's CV against the job requirements and identify gaps.

        JOB ROLE: {role}
        EXPERIENCE LEVEL REQUIRED: {experience_level}
        REQUIRED SKILLS: {", ".join(required_skills)}
        KEY RESPONSIBILITIES: {chr(10).join(responsibilities)}
        IMPORTANT KEYWORDS: {", ".join(keywords)}

        APPLICANT CV:
        {cv_raw_text}

        Identify all gaps, assign severity, provide actionable advice for each.
        Give an honest match score and overall assessment.
    """)

    # invoke structured LLM — returns GapReport pydantic object
    result = structured_llm.invoke([system_prompt, human_message])

    # build qa_flags dict with full gap report data
    qa_flags = {
        "gaps": [gap.model_dump() for gap in result.gaps],   # list of gap dicts
        "match_score": result.match_score,                    # score out of 10
        "overall_assessment": result.overall_assessment       # one line summary
    }

    # return gap report into shared state
    return {"qa_flags": qa_flags}