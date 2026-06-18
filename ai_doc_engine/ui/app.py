import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine.llm_service import LLMService
from engine.rag_store import DocVectorStore
from engine.github_service import GitHubService
from engine.models import DraftUpdate
from ui.components.severity_badge import render_severity_badge
from ui.components.diff_viewer import render_diff

st.set_page_config(page_title="AI Doc Engine", layout="wide")

llm = LLMService()
db = DocVectorStore()
git_service = GitHubService()

st.title("📖 AI-Powered Developer Docs")

tab1, tab2, tab3 = st.tabs(["💬 Documentation Chat", "⚠️ Pending Updates", "⚙️ Settings & Ingestion"])

# ── Tab 1: Chat ──────────────────────────────────────────────────────────────
with tab1:
    st.subheader("Chat with your Codebase")
    user_query = st.text_input("Ask a question about the code:")
    if user_query:
        with st.spinner("Searching docs..."):
            context_chunks = db.search(user_query)
            context_str = "\n\n".join(context_chunks)

            if not context_str:
                st.warning("No documentation found. Go to the Settings tab to ingest your code.")
            else:
                answer = llm.chat_with_context(user_query, context_str)
                st.markdown("### Answer")
                st.write(answer)
                with st.expander("View Source Context"):
                    st.text(context_str)

# ── Tab 2: Pending Updates ────────────────────────────────────────────────────
with tab2:
    st.subheader("Stale Documentation Flags")
    st.caption("Reading real-time flags from the Cloud Queue.")

    raw_queue = db.get_queue()

    if not raw_queue:
        st.success("All documentation is perfectly up to date! No pending changes.")
    else:
        st.markdown(f"**{len(raw_queue)} file(s) flagged for review**")
        st.markdown("---")

        for i, item in enumerate(raw_queue):
            draft = DraftUpdate.from_dict(item)

            # Header row: filename + severity badge
            col_title, col_badge = st.columns([4, 2])
            with col_title:
                st.markdown(f"#### 📄 `{draft.filename}`")
            with col_badge:
                render_severity_badge(draft.severity)

            # Reasoning callout
            if draft.reasoning:
                st.markdown(
                    f'<div style="background:#f0f4ff;border-left:4px solid #4a6cf7;'
                    f'padding:10px 14px;border-radius:4px;margin-bottom:12px;font-size:14px;">'
                    f'<strong>AI Reasoning:</strong> {draft.reasoning}</div>',
                    unsafe_allow_html=True,
                )

            # Diff viewer
            with st.expander("🔍 View Diff (old → new)", expanded=False):
                render_diff(draft.diff)

            # Side-by-side doc editor
            col_old, col_new = st.columns(2)
            with col_old:
                st.markdown("**Old Documentation**")
                st.text_area(
                    "Original (read-only)",
                    draft.old_doc,
                    height=350,
                    key=f"old_{i}",
                    disabled=True,
                )
            with col_new:
                st.markdown("**AI Drafted Update**")
                edited_draft = st.text_area(
                    "Review & Edit Draft",
                    draft.new_doc_draft,
                    height=350,
                    key=f"new_{i}",
                )

            # Action buttons
            col_approve, col_reject, _ = st.columns([2, 2, 8])
            with col_approve:
                if st.button("✅ Approve", key=f"btn_approve_{i}"):
                    db.upsert_doc(
                        doc_id=draft.filename,
                        text=edited_draft,
                        metadata={"filename": draft.filename},
                    )
                    raw_queue.pop(i)
                    db.save_queue(raw_queue)
                    st.success(f"Documentation for `{draft.filename}` updated.")
                    st.rerun()
            with col_reject:
                if st.button("❌ Reject", key=f"btn_reject_{i}"):
                    raw_queue.pop(i)
                    db.save_queue(raw_queue)
                    st.info(f"Flag for `{draft.filename}` dismissed.")
                    st.rerun()

            st.markdown("---")

# ── Tab 3: Ingestion ──────────────────────────────────────────────────────────
with tab3:
    st.subheader("Repository Ingestion")
    st.write(f"**Target Repo:** `{os.getenv('TARGET_REPO')}`")
    st.write("Click below to fetch all existing files, generate AI documentation, and save it to the database.")

    if st.button("Ingest Entire Repository"):
        with st.spinner("Fetching files and generating docs via Groq... This may take a minute."):
            contents = git_service.repo.get_contents("")
            processed_count = 0

            while contents:
                file_content = contents.pop(0)
                if file_content.type == "dir":
                    contents.extend(git_service.repo.get_contents(file_content.path))
                elif file_content.path.endswith(('.py', '.sql', '.java', '.md', '.txt')):
                    code = git_service.get_file_content(file_content.path)
                    if code.strip():
                        doc = llm.generate_documentation(f"File: {file_content.path}\n\n{code}")
                        db.upsert_doc(
                            doc_id=file_content.path,
                            text=f"File: {file_content.path}\n\n{doc}",
                            metadata={"filename": file_content.path},
                        )
                        processed_count += 1

            st.success(f"✅ Successfully generated and embedded documentation for {processed_count} files!")
