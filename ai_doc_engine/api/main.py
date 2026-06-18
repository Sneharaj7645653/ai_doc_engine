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

# Changed from chroma_db to a generic shared data folder
UPDATES_FILE = "/app/data/pending_updates.json"

def process_webhook_commit():
    print("🔍 BACKGROUND TASK STARTED: Fetching latest commit...", flush=True)
    changes = git_service.get_latest_commit_diffs()
    print(f"📦 Found {len(changes)} changed files in the latest commit.", flush=True)
    
    # Ensure the shared data directory actually exists
    os.makedirs(os.path.dirname(UPDATES_FILE), exist_ok=True)
    
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
        print(f"📄 Checking file: {filename}", flush=True)
        
        # CLEANED UP: No more ChromaDB .collection calls! Just use Pinecone.
        old_doc = db.get_doc(filename)
        
        if not old_doc:
            print(f"⚠️ {filename} was not found in the Vector Database. Skipping.", flush=True)
            continue
            
        if patch:
            print(f"🧠 Sending {filename} to Llama 3.3 for staleness check...", flush=True)
            analysis = llm_service.detect_staleness_and_draft(old_doc, patch)
            
            severity = "REVIEW_RECOMMENDED"
            updated_doc = analysis 
            
            if "SEVERITY:" in analysis and "UPDATED_DOC:" in analysis:
                parts = analysis.split("UPDATED_DOC:")
                severity = parts[0].replace("SEVERITY:", "").strip()
                updated_doc = parts[1].strip()
            
            print(f"🤖 AI Verdict for {filename}: {severity}", flush=True)
            
            if "SAFE" not in severity.upper():
                pending_updates.append({
                    "filename": filename,
                    "severity": severity,
                    "old_doc": old_doc,
                    "new_doc_draft": updated_doc
                })
                print(f"✅ Added {filename} to UI Review Queue.", flush=True)
    
    with open(UPDATES_FILE, "w") as f:
        json.dump(pending_updates, f)
        
    print(f"🏁 Background task complete. Saved {len(pending_updates)} flags total.", flush=True)

@app.post("/webhook/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    print("🔔 WEBHOOK RECEIVED from GitHub!", flush=True)
    if "commits" in payload:
        print("✅ Push event detected. Triggering AI analysis...", flush=True)
        background_tasks.add_task(process_webhook_commit)
    else:
        print("ℹ️ Webhook received, but it wasn't a code push (commits array missing).", flush=True)
    return {"status": "Webhook received"}