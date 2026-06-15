from fastapi import FastAPI, Request, BackgroundTasks
import uvicorn
import json
import os
from engine.github_service import GitHubService
from engine.llm_service import LLMService
from engine.rag_store import DocVectorStore

app = FastAPI(title="AI Doc Engine API")
git_service = GitHubService()
llm_service = LLMService()
db = DocVectorStore()

# We use the shared ChromaDB folder to pass messages to the UI
UPDATES_FILE = "/app/chroma_db/pending_updates.json"

def process_webhook_commit():
    """Background task to evaluate code changes and flag staleness."""
    changes = git_service.get_latest_commit_diffs()
    
    # Load existing pending updates queue
    if os.path.exists(UPDATES_FILE):
        with open(UPDATES_FILE, "r") as f:
            try:
                pending_updates = json.load(f)
            except json.JSONDecodeError:
                pending_updates = []
    else:
        pending_updates = []

    for change in changes:
        filename = change["filename"]
        patch = change["patch"]
        
        # 1. Fetch the old doc from ChromaDB using the filename as the ID
        try:
            result = db.collection.get(ids=[filename])
            old_doc = result['documents'][0] if result['documents'] else None
        except Exception:
            old_doc = None
        
        if old_doc and patch:
            # 2. Ask Llama 3 to analyze staleness and draft an update
            analysis = llm_service.detect_staleness_and_draft(old_doc, patch)
            
            # 3. Parse the specific formatting requested in llm_service.py
            severity = "REVIEW_RECOMMENDED"
            updated_doc = analysis 
            
            if "SEVERITY:" in analysis and "UPDATED_DOC:" in analysis:
                parts = analysis.split("UPDATED_DOC:")
                severity = parts[0].replace("SEVERITY:", "").strip()
                updated_doc = parts[1].strip()
            
            # 4. Save to the queue if the documentation is affected
            if "SAFE" not in severity.upper():
                pending_updates.append({
                    "filename": filename,
                    "severity": severity,
                    "old_doc": old_doc,
                    "new_doc_draft": updated_doc
                })
    
    # Write the updated flags back to the shared file
    with open(UPDATES_FILE, "w") as f:
        json.dump(pending_updates, f)
        
    print(f"Processed {len(changes)} changes. Saved {len(pending_updates)} flags.")

@app.post("/webhook/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    # Trigger the background analysis when code is pushed
    if "commits" in payload:
        background_tasks.add_task(process_webhook_commit)
    return {"status": "Webhook received"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)