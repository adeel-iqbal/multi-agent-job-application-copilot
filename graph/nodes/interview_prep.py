# interview_prep.py — generates personalized interview Q&A
# uses JD analysis + CV text + approved cover letter as full context
# handles follow-up requests from HITL 2 (more questions, different focus)

import os                                                    # for env variables
from dotenv import load_dotenv                               # load .env file
from langchain_openai import ChatOpenAI                      # OpenAI LLM
from langchain_core.messages import SystemMessage, HumanMessage  # message types
from pydantic import BaseModel, Field                        # structured output
from typing import List                                      # typed list
from graph.state import AppState                             # shared state

# load environment variables
load_dotenv()


# --- Structured Output Schema ---
# each Q&A pair is a clean typed object

class QAPair(BaseModel):
    """A single interview question with a personalized suggested answer"""

    # the interview question
    question: str = Field(description="The interview question")

    # category helps user know what kind of question this is
    category: str = Field(description="Category: role-specific, behavioral, situational, or gap-related")

    # suggested answer drawn from user's actual CV content
    suggested_answer: str = Field(description="Personalized suggested answer based on the applicant's CV")


class InterviewQAList(BaseModel):
    """Full list of interview Q&A pairs"""

    # list of all Q&A pairs
    qa_pairs: List[QAPair] = Field(description="List of interview questions with suggested answers")


def prepare_interview(state: AppState) -> dict:
    """
    Interview Prep Agent node — generates categorized Q&A.
    Uses full context: JD analysis + CV + approved cover letter.
    If hitl_2_feedback exists, generates additional/focused questions.
    Writes result into state['interview_qa'].
    """

    # initialize OpenAI LLM
    llm = ChatOpenAI(
        model="gpt-4o",                         # latest capable model
        temperature=0.4,                        # some variety but still grounded
        api_key=os.getenv("OPENAI_API_KEY")     # key from .env
    )

    # bind structured output schema
    structured_llm = llm.with_structured_output(InterviewQAList)

    # pull context from shared state
    jd_analysis = state.get("jd_analysis", {})
    cv_raw_text = state.get("cv_raw_text", "")
    cover_letter_final = state.get("cover_letter_final", "")   # approved letter
    hitl_2_feedback = state.get("hitl_2_feedback", "")         # user request at HITL 2
    existing_qa = state.get("interview_qa", [])                # already generated Q&A

    # extract from jd_analysis
    role = jd_analysis.get("role", "the role")
    required_skills = ", ".join(jd_analysis.get("required_skills", []))
    responsibilities = "\n".join(jd_analysis.get("responsibilities", []))
    experience_level = jd_analysis.get("experience_level", "")

    # system prompt — strict rules for quality Q&A generation
    system_prompt = SystemMessage(content=f"""
        You are an expert interview coach with deep knowledge of hiring processes.
        You generate realistic, role-specific interview questions and personalized answers.

        Rules:
        - Questions must be realistic and actually asked in interviews for: {role}
        - Suggested answers must be grounded in the applicant's actual CV — no fabrication
        - Cover all categories: role-specific, behavioral, situational, gap-related
        - Behavioral questions should follow STAR format hints in suggested answers
        - Suggested answers should be 3-5 sentences, specific and confident
    """)

    # build prompt based on whether this is first gen or HITL 2 follow-up
    if hitl_2_feedback and hitl_2_feedback.lower() != "accept":

        # --- FOLLOW-UP PATH ---
        # user wants more questions or a specific focus area
        human_message = HumanMessage(content=f"""
            The applicant already has these interview questions generated:
            {existing_qa}

            USER REQUEST FOR MORE:
            {hitl_2_feedback}

            Generate ADDITIONAL questions based on the user's request.
            Do not repeat questions already generated.

            JOB ROLE: {role}
            REQUIRED SKILLS: {required_skills}
            EXPERIENCE LEVEL: {experience_level}

            APPLICANT CV:
            {cv_raw_text}

            APPROVED COVER LETTER:
            {cover_letter_final}
        """)

    else:

        # --- FIRST GENERATION PATH ---
        # generate default 12 questions across all categories
        human_message = HumanMessage(content=f"""
            Generate exactly 12 interview questions with personalized suggested answers.

            Distribution:
            - 4 role-specific questions (based on required skills and responsibilities)
            - 3 behavioral questions (based on CV experience, STAR format hints)
            - 3 situational questions (hypothetical scenarios for this role)
            - 2 gap-related questions (areas where CV may not fully match JD)

            JOB ROLE: {role}
            REQUIRED SKILLS: {required_skills}
            KEY RESPONSIBILITIES:
            {responsibilities}
            EXPERIENCE LEVEL: {experience_level}

            APPLICANT CV:
            {cv_raw_text}

            APPROVED COVER LETTER:
            {cover_letter_final}

            Ground every suggested answer in the applicant's actual CV content.
        """)

    # invoke structured LLM — returns InterviewQAList pydantic object
    result = structured_llm.invoke([system_prompt, human_message])

    # convert each QAPair to dict and build the full list
    qa_list = [qa.model_dump() for qa in result.qa_pairs]

    # if this is a follow-up, APPEND new Q&A to existing ones
    # if first generation, just use the new list
    if hitl_2_feedback and hitl_2_feedback.lower() != "accept" and existing_qa:
        qa_list = existing_qa + qa_list    # merge old + new questions

    # return updated Q&A list into shared state
    return {"interview_qa": qa_list}