# cover_letter.py — generates a personalized cover letter
# uses JD analysis + raw CV text to write a targeted letter
# also handles regeneration if user sends feedback at HITL 1

import os                                                    # for env variables
from dotenv import load_dotenv                               # load .env file
from langchain_openai import ChatOpenAI                      # OpenAI LLM
from langchain_core.messages import SystemMessage, HumanMessage  # message types
from graph.state import AppState                             # shared state

# load environment variables from .env
load_dotenv()


def write_cover_letter(state: AppState) -> dict:
    """
    Cover Letter Agent node — writes a personalized cover letter.
    Uses jd_analysis + cv_raw_text from state.
    If hitl_1_feedback exists, it means user requested changes — regenerate accordingly.
    Writes result into state['cover_letter_draft'].
    """

    # initialize OpenAI LLM
    llm = ChatOpenAI(
        model="gpt-4o",                          # latest capable model
        temperature=0.4,                         # slight creativity for natural writing
        api_key=os.getenv("OPENAI_API_KEY")      # key from .env
    )

    # pull what we need from shared state
    jd_analysis = state.get("jd_analysis", {})          # structured JD info
    cv_raw_text = state.get("cv_raw_text", "")          # parsed CV text
    hitl_feedback = state.get("hitl_1_feedback", "")    # user feedback if regenerating

    # extract fields from jd_analysis dict for cleaner prompt building
    role = jd_analysis.get("role", "the role")
    required_skills = ", ".join(jd_analysis.get("required_skills", []))
    responsibilities = "\n".join(jd_analysis.get("responsibilities", []))
    tone = jd_analysis.get("tone", "professional")
    keywords = ", ".join(jd_analysis.get("keywords", []))
    experience_level = jd_analysis.get("experience_level", "")

# system prompt — defines the agent's role and rules
    system_prompt = SystemMessage(content=f"""
        You are an expert cover letter writer with 10+ years of hiring experience.
        You write compelling, personalized cover letters that get interviews.

        Rules:
        - Always open with exactly "Hi there,"
        - Always maintain professional tone throughout
        - Be specific and concise — Maximum 250 words total
        - Always close with "Best regards," or "Sincerely,"
        - Do NOT use generic phrases like "I am writing to apply for..."
        - Do NOT fabricate experience not present in the CV
        - Naturally weave in these keywords: {keywords}
        - Keep it to exactly 3 paragraphs, concise and impactful
        - End with a confident, specific call to action
    """)

    # build human message differently based on whether this is
    # a first generation or a regeneration after HITL feedback
    if hitl_feedback and hitl_feedback.lower() != "approve":

        # --- REGENERATION PATH ---
        # user gave feedback at HITL 1, incorporate it into new version
        human_message = HumanMessage(content=f"""
            Here is the previously generated cover letter and the user's feedback.
            Rewrite the cover letter incorporating the feedback precisely.

            PREVIOUS COVER LETTER:
            {state.get('cover_letter_draft', '')}

            USER FEEDBACK:
            {hitl_feedback}

            JOB ROLE: {role}
            REQUIRED SKILLS: {required_skills}
            EXPERIENCE LEVEL: {experience_level}

            APPLICANT CV:
            {cv_raw_text}

            Write an improved cover letter based on the feedback above.
        """)

    else:

        # --- FIRST GENERATION PATH ---
        # fresh cover letter generation from JD + CV
        human_message = HumanMessage(content=f"""
            Write a personalized cover letter for the following:

            JOB ROLE: {role}
            REQUIRED SKILLS: {required_skills}
            KEY RESPONSIBILITIES:
            {responsibilities}
            EXPERIENCE LEVEL: {experience_level}

            APPLICANT CV:
            {cv_raw_text}

            Write a compelling cover letter that highlights relevant experience
            and directly addresses the role requirements.
        """)

    # invoke LLM — returns AIMessage, we extract .content for plain text
    response = llm.invoke([system_prompt, human_message])

    # store draft in state — HITL 1 will let user review this
    return {"cover_letter_draft": response.content}