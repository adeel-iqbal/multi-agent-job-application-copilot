# assembler.py — final node in the pipeline
# bundles cover letter + interview Q&A + gap report into clean final output
# no LLM needed here — pure data assembly and formatting

from graph.state import AppState     # shared state


def assemble_output(state: AppState) -> dict:
    """
    Assembler node — collects all agent outputs from state
    and formats them into a clean final package dict.
    This dict is what Chainlit reads to render the output cards.
    """

    # pull final cover letter — approved by user at HITL 1
    cover_letter = state.get("cover_letter_final", "")

    # fallback to draft if final not set for any reason
    if not cover_letter:
        cover_letter = state.get("cover_letter_draft", "No cover letter generated.")

    # pull interview Q&A list
    interview_qa = state.get("interview_qa", [])

    # pull gap report dict
    qa_flags = state.get("qa_flags", {})
    gaps = qa_flags.get("gaps", [])
    match_score = qa_flags.get("match_score", 0)
    overall_assessment = qa_flags.get("overall_assessment", "")

    # pull JD analysis for summary header
    jd_analysis = state.get("jd_analysis", {})
    role = jd_analysis.get("role", "the role")
    experience_level = jd_analysis.get("experience_level", "")

    # --- build formatted cover letter section ---
    cover_letter_section = {
        "title": "Cover Letter",                  # card title
        "role": role,                             # for card subtitle
        "content": cover_letter                   # full letter text
    }

    # --- build formatted Q&A section ---
    # each item has question, category, suggested_answer
    qa_section = {
        "title": "Interview Preparation",         # card title
        "total_questions": len(interview_qa),     # count for display
        "qa_pairs": interview_qa                  # full Q&A list
    }

    # --- build formatted gap report section ---
    # color coding severity for UI display
    severity_colors = {
        "critical": "🔴",     # red dot for critical gaps
        "moderate": "🟡",     # yellow dot for moderate gaps
        "minor": "🟢"         # green dot for minor gaps
    }

    # add color indicator to each gap for Chainlit display
    formatted_gaps = []
    for gap in gaps:
        formatted_gap = {
            "gap": gap.get("gap", ""),
            "severity": gap.get("severity", "minor"),
            "severity_icon": severity_colors.get(
                gap.get("severity", "minor"), "🟢"   # default to green if unknown
            ),
            "advice": gap.get("advice", "")
        }
        formatted_gaps.append(formatted_gap)

    gap_section = {
        "title": "Gap Report",                    # card title
        "match_score": match_score,               # score out of 10
        "overall_assessment": overall_assessment, # one line summary
        "gaps": formatted_gaps                    # formatted gap list
    }

    # --- build complete final output package ---
    final_output = {
        "cover_letter": cover_letter_section,
        "interview_qa": qa_section,
        "gap_report": gap_section,
        "meta": {
            "role": role,                         # role applied for
            "experience_level": experience_level, # seniority level
            "total_questions": len(interview_qa), # total Q&A generated
            "total_gaps": len(gaps),              # total gaps found
            "match_score": match_score            # overall match score
        }
    }

    # return final output into shared state
    # Chainlit app.py will read this to render the output cards
    return {"final_output": final_output}