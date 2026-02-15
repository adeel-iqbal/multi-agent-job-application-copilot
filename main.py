# # app.py — Chainlit entry point
# # handles user interaction, runs LangGraph pipeline, manages HITL points
# import os
# import uuid
# import chainlit as cl
# from dotenv import load_dotenv
# from graph.graph import graph

# load_dotenv()

# # --- Chat Start ---
# # runs once when user opens the app in browser

# @cl.on_chat_start
# async def on_chat_start():

#     # generate unique thread_id for this user session
#     # MemorySaver uses this to store and retrieve state across HITL pauses
#     thread_id = str(uuid.uuid4())

#     # store thread_id in Chainlit user session
#     # cl.user_session persists data across messages in same chat
#     cl.user_session.set("thread_id", thread_id)

#     # store pipeline stage tracker
#     # stages: "awaiting_input" → "running" → "hitl_1" → "hitl_2" → "done"
#     cl.user_session.set("stage", "awaiting_input")

#     # welcome message with instructions
#     await cl.Message(content="""
# 👋 **Welcome to Job Application Copilot**

# I'll help you prepare a complete job application package.

# **To get started, please provide:**
# 1. 📄 Upload your **CV** (PDF or DOCX) using the attachment button
# 2. 📋 Paste the **Job Description** text in your message

# Send both together and I'll get to work!
#     """).send()

# # --- Main Message Handler ---
# # runs every time user sends a message

# @cl.on_message
# async def on_message(message: cl.Message):

#     # get current stage and thread_id from session
#     stage = cl.user_session.get("stage")
#     thread_id = cl.user_session.get("thread_id")

#     # LangGraph config — thread_id links this run to saved state in MemorySaver
#     config = {"configurable": {"thread_id": thread_id}}

#     # ================================================================
#     # STAGE 1 — awaiting_input
#     # user sends CV file + JD text to kick off the pipeline
#     # ================================================================
#     if stage == "awaiting_input":
#         await handle_initial_input(message, config)

#     # ================================================================
#     # STAGE 2 — hitl_1
#     # user reviews cover letter draft and sends approval or feedback
#     # ================================================================
#     elif stage == "hitl_1":
#         await handle_hitl_1(message, config)

#     # ================================================================
#     # STAGE 3 — hitl_2
#     # user reviews Q&A and sends acceptance or requests more questions
#     # ================================================================
#     elif stage == "hitl_2":
#         await handle_hitl_2(message, config)

#     # ================================================================
#     # STAGE 4 — done
#     # pipeline finished, inform user
#     # ================================================================
#     elif stage == "done":
#         await cl.Message(content="✅ Your application package is complete! Start a new chat to prepare for another role.").send()

# # --- Handler: Initial Input ---
# # processes CV file upload + JD text, starts the graph

# async def handle_initial_input(message: cl.Message, config: dict):

#     # check if user attached a file
#     if not message.elements:
#         await cl.Message(content="⚠️ Please attach your CV file (PDF or DOCX) along with the job description.").send()
#         return

#     # check if user provided JD text
#     if not message.content.strip():
#         await cl.Message(content="⚠️ Please paste the job description text in your message.").send()
#         return

#     # get the uploaded file from message elements
#     uploaded_file = message.elements[0]

#     # check file extension is PDF or DOCX only
#     allowed_extensions = [".pdf", ".docx"]
#     file_extension = os.path.splitext(uploaded_file.name)[1].lower()

#     if file_extension not in allowed_extensions:
#         await cl.Message(content=f"⚠️ Unsupported file type **{file_extension}**. Please upload a PDF or DOCX file only.").send()
#         return

#     # get file path directly from Chainlit's temp storage
#     cv_file_path = uploaded_file.path
    
#     # notify user pipeline is starting
#     await cl.Message(content="🚀 Got it! Starting your application pipeline...\n\n⏳ Parsing CV and analyzing job description...").send()

#     # build initial state to feed into graph
#     initial_state = {
#         "job_description": message.content.strip(),   # JD text from message
#         "cv_file_path": cv_file_path,                 # path to saved CV file
#         "messages": []                                # empty message history
#     }

#     # run graph — it will run until it hits interrupt_before hitl_1
#     await cl.Message(content="✍️ Writing your cover letter...").send()

#     # stream graph execution — async_stream yields events as nodes run
#     async for event in graph.astream(initial_state, config=config):
#         # each event is a dict of {node_name: output_dict}
#         # we just let nodes run silently until graph pauses at hitl_1
#         pass

#     # graph has paused at hitl_1 — get current state to read cover letter draft
#     current_state = graph.get_state(config)
#     cover_letter_draft = current_state.values.get("cover_letter_draft", "")

#     # display cover letter draft to user
#     await cl.Message(content=f"""
# ✅ **Cover Letter Draft Ready!**

# ---

# {cover_letter_draft}

# ---

# **What would you like to do?**
# - Type **`approve`** to accept this cover letter and continue
# - Type your **feedback/changes** and I'll rewrite it
#     """).send()

#     # update stage to hitl_1 — next message will be handled by hitl_1 handler
#     cl.user_session.set("stage", "hitl_1")

# # --- Handler: HITL 1 ---
# # user reviews cover letter, approves or requests changes

# async def handle_hitl_1(message: cl.Message, config: dict):

#     # get user feedback from message
#     user_feedback = message.content.strip()

#     # update state with user feedback by resuming graph with new state values
#     graph.update_state(
#         config,
#         {"hitl_1_feedback": user_feedback}     # inject feedback into state
#     )

#     # check if user approved or wants changes
#     if user_feedback.lower() == "approve":
#         await cl.Message(content="✅ Cover letter approved! Generating interview questions...").send()
#     else:
#         await cl.Message(content=f"✏️ Got it! Rewriting cover letter with your feedback...").send()

#     # resume graph from hitl_1 — runs until next interrupt (hitl_2)
#     async for event in graph.astream(None, config=config):
#         pass

#     # graph paused at hitl_2 — get current state to read Q&A
#     current_state = graph.get_state(config)
#     interview_qa = current_state.values.get("interview_qa", [])

#     # if cover letter was regenerated, show new version first
#     if user_feedback.lower() != "approve":
#         new_draft = current_state.values.get("cover_letter_draft", "")

#         await cl.Message(content=f"""
# ✅ **Cover Letter Rewritten!**

# ---

# {new_draft}

# ---

# Type **`approve`** to accept or provide more feedback.
#         """).send()

#         # stay in hitl_1 stage for another review round
#         return

#     # format and display Q&A list
#     qa_display = "✅ **Interview Questions Ready!**\n\n"
#     for i, qa in enumerate(interview_qa, 1):
#         qa_display += f"""
# **Q{i} [{qa.get('category', '').upper()}]**
# {qa.get('question', '')}

# 💡 *Suggested Answer:*
# {qa.get('suggested_answer', '')}

# ---
# """

#     await cl.Message(content=qa_display).send()

#     # prompt user for HITL 2 action
#     await cl.Message(content="""
# **What would you like to do?**
# - Type **`accept`** to proceed to the gap report and final output
# - Type a request for **more questions** (e.g. "give me 5 more on system design")
#     """).send()

#     # update stage to hitl_2
#     cl.user_session.set("stage", "hitl_2")

# # --- Handler: HITL 2 ---
# # user reviews Q&A, accepts or requests more questions

# async def handle_hitl_2(message: cl.Message, config: dict):

#     # get user feedback from message
#     user_feedback = message.content.strip()

#     # inject hitl_2_feedback into state
#     graph.update_state(
#         config,
#         {"hitl_2_feedback": user_feedback}
#     )

#     if user_feedback.lower() == "accept":
#         await cl.Message(content="✅ Interview questions accepted! Running gap analysis and assembling your package...").send()
#     else:
#         await cl.Message(content=f"➕ Generating more questions based on: *{user_feedback}*...").send()

#     # resume graph from hitl_2 — runs until END
#     async for event in graph.astream(None, config=config):
#         pass

#     # get final state
#     current_state = graph.get_state(config)

#     # if user requested more questions — show updated Q&A and stay in hitl_2
#     if user_feedback.lower() != "accept":
#         interview_qa = current_state.values.get("interview_qa", [])

#         qa_display = "➕ **Updated Interview Questions:**\n\n"
#         for i, qa in enumerate(interview_qa, 1):
#             qa_display += f"""
# **Q{i} [{qa.get('category', '').upper()}]**
# {qa.get('question', '')}

# 💡 *Suggested Answer:*
# {qa.get('suggested_answer', '')}

# ---
# """
#         await cl.Message(content=qa_display).send()
#         await cl.Message(content="Type **`accept`** to proceed or request more questions.").send()
#         return

#     # pipeline complete — render final output cards
#     final_output = current_state.values.get("final_output", {})
#     await render_final_output(final_output)

#     # update stage to done
#     cl.user_session.set("stage", "done")

# # --- Render Final Output ---
# # formats and displays the three output cards

# async def render_final_output(final_output: dict):

#     # extract three sections from final output
#     cover_letter_data = final_output.get("cover_letter", {})
#     qa_data = final_output.get("interview_qa", {})
#     gap_data = final_output.get("gap_report", {})
#     meta = final_output.get("meta", {})

#     # --- summary header ---
#     await cl.Message(content=f"""
# 🎉 **Your Application Package is Ready!**

# 📋 Role: **{meta.get('role', '')}**
# 🎯 Match Score: **{meta.get('match_score', 0)}/10**
# ❓ Questions Generated: **{meta.get('total_questions', 0)}**
# ⚠️ Gaps Found: **{meta.get('total_gaps', 0)}**
#     """).send()

#     # --- card 1: cover letter ---
#     await cl.Message(content=f"""
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📄 **COVER LETTER**
# *{cover_letter_data.get('role', '')}*
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# {cover_letter_data.get('content', '')}
#     """).send()

#     # --- card 2: interview Q&A ---
#     qa_pairs = qa_data.get("qa_pairs", [])
#     qa_card = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
#     qa_card += f"❓ **INTERVIEW PREPARATION** ({qa_data.get('total_questions', 0)} Questions)\n"
#     qa_card += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

#     for i, qa in enumerate(qa_pairs, 1):
#         qa_card += f"**Q{i} [{qa.get('category', '').upper()}]**\n"
#         qa_card += f"{qa.get('question', '')}\n\n"
#         qa_card += f"💡 *{qa.get('suggested_answer', '')}*\n\n"
#         qa_card += "---\n"

#     await cl.Message(content=qa_card).send()

#     # --- card 3: gap report ---
#     gaps = gap_data.get("gaps", [])
#     gap_card = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
#     gap_card += f"⚠️ **GAP REPORT** — {gap_data.get('overall_assessment', '')}\n"
#     gap_card += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

#     for gap in gaps:
#         gap_card += f"{gap.get('severity_icon', '🟢')} **{gap.get('gap', '')}** "
#         gap_card += f"*({gap.get('severity', '').upper()})*\n"
#         gap_card += f"→ {gap.get('advice', '')}\n\n"

#     await cl.Message(content=gap_card).send()

#     # final sign-off message
#     await cl.Message(content="✅ **All done! Good luck with your application. You've got this! 🚀**").send()