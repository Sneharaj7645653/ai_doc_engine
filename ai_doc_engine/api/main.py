from fastapi import FastAPI, Request, BackgroundTasks
import uvicorn
from engine.github_service import GitHubService
from engine.llm_service import LLMService
from engine.rag_store import DocVectorStore
from engine.models import StalenessFlag
from engine.update_drafter import UpdateDrafter

app = FastAPI(title="AI Doc Engine API")
git_service = GitHubService()
llm_service = LLMService()
db = DocVectorStore()
drafter = UpdateDrafter(llm_service)


def process_webhook_commit():
    print("🔍 BACKGROUND TASK STARTED: Fetching latest commit...", flush=True)
    changes = git_service.get_latest_commit_diffs()
    print(f"📦 Found {len(changes)} changed files in the latest commit.", flush=True)

    pending_updates = db.get_queue()

    for change in changes:
        filename = change["filename"]
        patch = change.get("patch", "")
        print(f"📄 Checking file: {filename}", flush=True)

        old_doc = db.get_doc(filename)
        if not old_doc:
            print(f"⚠️  {filename} not found in Vector DB. Skipping.", flush=True)
            continue

        if not patch:
            continue

        print(f"🧠 Drafting update for {filename}...", flush=True)
        flag = StalenessFlag(filename=filename, patch=patch, old_doc=old_doc)
        draft = drafter.draft(flag)

        print(f"🤖 AI Verdict for {filename}: {draft.severity}", flush=True)

        if "SAFE" not in draft.severity.upper():
            # Deduplicate: remove any existing entry for this file
            pending_updates = [u for u in pending_updates if u["filename"] != filename]
            pending_updates.append(draft.to_dict())
            print(f"✅ Added {filename} to UI Review Queue.", flush=True)

    db.save_queue(pending_updates)
    print(f"🏁 Background task complete. Queue size: {len(pending_updates)}.", flush=True)


@app.post("/webhook/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    print("🔔 WEBHOOK RECEIVED from GitHub!", flush=True)
    if "commits" in payload:
        print("✅ Push event detected. Triggering AI analysis...", flush=True)
        background_tasks.add_task(process_webhook_commit)
    else:
        print("ℹ️  Webhook received, but no commits array found.", flush=True)
    return {"status": "Webhook received"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
