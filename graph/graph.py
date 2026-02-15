# graph.py — builds and compiles the full LangGraph pipeline
# wires all nodes together, defines edges, sets HITL interrupt points

from langgraph.graph import StateGraph, START, END          # core graph building blocks
from langgraph.checkpoint.memory import MemorySaver         # in-memory checkpointer for HITL persistence
from graph.state import AppState                            # our shared state
from graph.nodes.parser import parse_cv                     # node 1 — CV file parser
from graph.nodes.jd_analyzer import analyze_jd              # node 2 — JD analyzer
from graph.nodes.cover_letter import write_cover_letter     # node 3 — cover letter writer
from graph.nodes.interview_prep import prepare_interview    # node 4 — interview Q&A generator
from graph.nodes.qa_agent import run_qa_check               # node 5 — gap analyzer
from graph.nodes.assembler import assemble_output           # node 6 — final assembler


# --- HITL Router Functions ---
# these are conditional edge functions
# they decide where to go AFTER a HITL interrupt resumes

def route_after_hitl_1(state: AppState) -> str:
    """
    Called after HITL 1 resumes.
    If user approved — move forward to interview prep.
    If user gave feedback — go back to cover letter agent to regenerate.
    """

    # get user feedback from state
    feedback = state.get("hitl_1_feedback", "").strip().lower()

    # if user typed "approve" or left empty — move forward
    if feedback == "approve" or feedback == "":
        return "proceed_to_interview"       # edge label — goes to interview_prep node

    # otherwise user gave edit instructions — regenerate cover letter
    return "regenerate_cover_letter"        # edge label — loops back to cover_letter node


def route_after_hitl_2(state: AppState) -> str:
    """
    Called after HITL 2 resumes.
    If user accepted — move forward to QA agent.
    If user requested more questions — loop back to interview prep.
    """

    # get user feedback from state
    feedback = state.get("hitl_2_feedback", "").strip().lower()

    # if user typed "accept" or left empty — move forward
    if feedback == "accept" or feedback == "":
        return "proceed_to_qa"              # edge label — goes to qa_agent node

    # otherwise user wants more/different questions — regenerate
    return "more_questions"                 # edge label — loops back to interview_prep node


# --- HITL Node Functions ---
# these nodes exist purely as interrupt points
# LangGraph pauses HERE and waits for human input before continuing

def hitl_1_node(state: AppState) -> dict:
    """
    HITL 1 pause point — after cover letter draft is ready.
    This node does nothing by itself.
    LangGraph interrupts HERE and waits for user input via Chainlit.
    User input is captured by app.py and written into state['hitl_1_feedback'].
    """
    # no processing — just a named pause point in the graph
    return {}


def hitl_2_node(state: AppState) -> dict:
    """
    HITL 2 pause point — after interview Q&A is generated.
    Same pattern as HITL 1 — pure pause point.
    User input captured by app.py written into state['hitl_2_feedback'].
    """
    # no processing — just a named pause point in the graph
    return {}


def set_cover_letter_final(state: AppState) -> dict:
    """
    Small utility node — runs when user approves cover letter at HITL 1.
    Copies cover_letter_draft into cover_letter_final in state.
    This way downstream agents always read from cover_letter_final.
    """

    # copy draft to final — this is the approved version
    return {"cover_letter_final": state.get("cover_letter_draft", "")}


# --- Build the Graph ---

def build_graph():
    """
    Builds and compiles the full LangGraph pipeline.
    Returns a compiled graph ready to be invoked by Chainlit.
    """

    # initialize StateGraph with our AppState schema
    graph_builder = StateGraph(AppState)

    # --- Add all nodes ---
    # each node is a function that takes state and returns a dict

    graph_builder.add_node("parse_cv", parse_cv)                        # node 1
    graph_builder.add_node("analyze_jd", analyze_jd)                    # node 2
    graph_builder.add_node("write_cover_letter", write_cover_letter)    # node 3
    graph_builder.add_node("hitl_1", hitl_1_node)                       # HITL 1 pause
    graph_builder.add_node("set_cover_letter_final", set_cover_letter_final)  # utility
    graph_builder.add_node("prepare_interview", prepare_interview)       # node 4
    graph_builder.add_node("hitl_2", hitl_2_node)                       # HITL 2 pause
    graph_builder.add_node("run_qa_check", run_qa_check)                # node 5
    graph_builder.add_node("assemble_output", assemble_output)          # node 6

    # --- Add edges — define the flow ---

    # START → parse CV first
    graph_builder.add_edge(START, "parse_cv")

    # parse CV → analyze JD (both run sequentially at start)
    graph_builder.add_edge("parse_cv", "analyze_jd")

    # analyze JD → write cover letter
    graph_builder.add_edge("analyze_jd", "write_cover_letter")

    # write cover letter → HITL 1 pause
    # graph stops here and waits for user
    graph_builder.add_edge("write_cover_letter", "hitl_1")

    # HITL 1 → conditional routing based on user feedback
    graph_builder.add_conditional_edges(
        "hitl_1",                           # from this node
        route_after_hitl_1,                 # call this router function
        {
            # router return value → next node name
            "proceed_to_interview": "set_cover_letter_final",   # approved
            "regenerate_cover_letter": "write_cover_letter"     # needs changes
        }
    )

    # set_cover_letter_final → prepare interview
    graph_builder.add_edge("set_cover_letter_final", "prepare_interview")

    # prepare interview → HITL 2 pause
    # graph stops here and waits for user again
    graph_builder.add_edge("prepare_interview", "hitl_2")

    # HITL 2 → conditional routing based on user feedback
    graph_builder.add_conditional_edges(
        "hitl_2",                           # from this node
        route_after_hitl_2,                 # call this router function
        {
            # router return value → next node name
            "proceed_to_qa": "run_qa_check",        # accepted Q&A
            "more_questions": "prepare_interview"   # wants more questions
        }
    )

    # run QA check → assemble final output
    graph_builder.add_edge("run_qa_check", "assemble_output")

    # assemble output → END
    graph_builder.add_edge("assemble_output", END)

    # --- Compile with checkpointer ---
    # MemorySaver enables state persistence across HITL interrupts
    # without this, state would be lost when graph pauses
    checkpointer = MemorySaver()

    # compile graph with:
    # checkpointer — for state persistence across interrupts
    # interrupt_before — list of nodes where graph pauses for human input
    compiled_graph = graph_builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["hitl_1", "hitl_2"]   # pause BEFORE these nodes run
    )

    return compiled_graph


# --- Singleton graph instance ---
# build once when module is imported
# Chainlit app.py imports this directly
graph = build_graph()