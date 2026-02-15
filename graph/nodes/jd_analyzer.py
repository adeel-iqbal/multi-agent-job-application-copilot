# jd_analyzer.py — uses OpenAI to extract structured info from the job description
# this is our first real LLM-powered agent node

import os                                        # to access env variables
from dotenv import load_dotenv                   # to load .env file
from langchain_openai import ChatOpenAI          # OpenAI LLM via LangChain
from langchain_core.messages import SystemMessage, HumanMessage  # message types
from pydantic import BaseModel, Field            # for structured output schema
from typing import List                          # for typed lists
from graph.state import AppState                 # our shared state

# load .env so OPENAI_API_KEY is available
load_dotenv()


# --- Structured Output Schema ---
# Pydantic model defines exactly what we want the LLM to return
# LangGraph will enforce this structure via with_structured_output()

class JDAnalysis(BaseModel):
    """Structured output schema for JD Analyzer Agent"""

    # job role/title extracted from JD
    role: str = Field(description="The job title or role being applied for")

    # list of required technical and soft skills
    required_skills: List[str] = Field(description="List of required skills mentioned in JD")

    # key responsibilities from the JD
    responsibilities: List[str] = Field(description="Key responsibilities listed in the JD")

    # writing tone of the JD — formal, casual, technical, startup etc.
    tone: str = Field(description="Overall tone of the JD: formal, casual, technical, startup-like etc.")

    # experience level expected
    experience_level: str = Field(description="Expected experience level: junior, mid, senior, lead etc.")

    # any keywords that should appear in cover letter / responses
    keywords: List[str] = Field(description="Important keywords from JD to use in cover letter and answers")


def analyze_jd(state: AppState) -> dict:
    """
    JD Analyzer node — reads job description from state,
    sends it to OpenAI, returns structured analysis.
    Writes result into state['jd_analysis'].
    """

    # initialize OpenAI LLM — gpt-4o is latest capable model
    llm = ChatOpenAI(
        model="gpt-4o",               # latest OpenAI model
        temperature=0,                # 0 = deterministic, we want consistent extraction
        api_key=os.getenv("OPENAI_API_KEY")  # load key from .env
    )

    # bind structured output schema to LLM
    # this forces the LLM to return a valid JDAnalysis object
    structured_llm = llm.with_structured_output(JDAnalysis)

    # system prompt — tells LLM exactly what its job is
    system_prompt = SystemMessage(content="""
        You are an expert job description analyzer.
        Your job is to extract structured information from job descriptions accurately.
        Be precise, concise, and extract only what is explicitly stated or strongly implied.
        Do not hallucinate skills or responsibilities not present in the JD.
    """)

    # human message — passes the actual JD text to the LLM
    human_message = HumanMessage(content=f"""
        Analyze the following job description and extract structured information:

        {state['job_description']}
    """)

    # invoke the LLM with our messages
    # structured_llm returns a JDAnalysis pydantic object directly
    jd_analysis_result = structured_llm.invoke([system_prompt, human_message])

    # convert pydantic object to dict so it can be stored in state
    # model_dump() is the pydantic v2 way to convert to dict
    return {"jd_analysis": jd_analysis_result.model_dump()}