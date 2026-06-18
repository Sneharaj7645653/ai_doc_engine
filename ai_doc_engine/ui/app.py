import streamlit as st
import sys
import os
import json

# Ensure engine modules can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine.llm_service import LLMService
from engine.rag_store import DocVectorStore
from engine.github_service import GitHubService

st.set_page_config(page_title="AI Doc Engine", layout="wide")

llm = LLMService()
db = DocVectorStore()
git_service = GitHubService()

st.title("📖 AI-Powered Developer Docs")

tab1, tab2, tab3 = st.tabs(["💬 Documentation Chat", "⚠️ Pending Updates", "⚙️ Settings & Ingestion"])

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

with tab2:
    st.subheader("Stale Documentation Flags")
    st.info("Reading real-time code changes from the Cloud Queue.")
    
    # Load the queue directly from Pinecone
    pending_updates = db.get_queue()

    if not pending_updates:
        st.success("All documentation is perfectly up to date! No pending changes.")
    else:
        for i, update in enumerate(pending_updates):
            st.markdown(f"#### 📄 `{update['filename']}`")
            
            # Color code the severity
            sev = update['severity'].upper()
            if "BROKEN" in sev:
                st.error(f"**Severity: {sev}**")
            elif "OUTDATED" in sev:
                st.warning(f"**Severity: {sev}**")
            else:
                st.info(f"**Severity: {sev}**")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Old Documentation**")
                st.text_area("Original (Read Only)", update['old_doc'], height=350, key=f"old_{i}", disabled=True)
            with col2:
                st.markdown("**AI Drafted Update**")
                edited_draft = st.text_area("Review & Edit Draft", update['new_doc_draft'], height=350, key=f"new_{i}")
                
            col_btn1, col_btn2 = st.columns([2, 10])
            with col_btn1:
                if st.button("✅ Approve Update", key=f"btn_app_{i}"):
                    # Update the Vector Database
                    db.upsert_doc(
                        doc_id=update['filename'],
                        text=edited_draft,
                        metadata={"filename": update['filename']}
                    )
                    
                    # Remove this item from the queue and save back to Pinecone
                    pending_updates.pop(i)
                    db.save_queue(pending_updates)
                    
                    st.success("Documentation updated and vector store refreshed!")
                    st.rerun()
            with col_btn2:
                if st.button("❌ Dismiss", key=f"btn_dis_{i}"):
                    # Remove from queue without updating docs
                    pending_updates.pop(i)
                    db.save_queue(pending_updates)
                    st.rerun()
                    
            st.markdown("---")

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
                            metadata={"filename": file_content.path}
                        )
                        processed_count += 1
                        
            st.success(f"✅ Successfully generated and embedded documentation for {processed_count} files!")