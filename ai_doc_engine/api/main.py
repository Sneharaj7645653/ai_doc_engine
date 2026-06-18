from fastapi import FastAPI, Request, BackgroundTasks
import uvicorn
import json
from engine.change_detector import ChangeDetector
from engine.github_service import GitHubService
from engine.llm_service import LLMService
from engine.rag_store import DocVectorStore
from engine.staleness_classifier import StalenessClassifier

app = FastAPI(title="AI Doc Engine API")
git_service = GitHubService()
llm_service = LLMService()
db = DocVectorStore()
change_detector = ChangeDetector()
staleness_classifier = StalenessClassifier()


def process_webhook_commit():
    print("[START] Background task started: fetching latest commit...", flush=True)
    changes = git_service.get_latest_commit_diffs()
    print(f"[INFO] Found {len(changes)} changed files in the latest commit.", flush=True)

    # Fetch queue directly from Pinecone
    pending_updates = db.get_queue()

    for change in changes:
        filename = change["filename"]
        patch = change.get("patch")
        print(f"[FILE] Checking file: {filename}", flush=True)

        if not patch:
            print(f"[SKIP] No patch found for {filename}. Skipping.", flush=True)
            continue

        old_doc = db.get_doc(filename)

        if not old_doc:
            print(
                f"[SKIP] {filename} was not found in the Vector Database. Skipping.",
                flush=True,
            )
            continue

        changed_units = change_detector.detect(patch)
        flag = staleness_classifier.classify(filename, changed_units)

        print(
            f"[RULES] Rule-based analysis for {filename}: "
            f"{len(changed_units)} changed units detected.",
            flush=True,
        )
        print(f"[SEVERITY] Severity for {filename}: {flag.severity}", flush=True)
        print(f"[REASON] Reason for {filename}: {flag.reason}", flush=True)

        if flag.severity == "SAFE":
            print(f"[SAFE] {filename} is safe. Skipping LLM analysis.", flush=True)
            continue

        print(f"[LLM] Sending {filename} to Llama 3.3 for staleness check...", flush=True)
        analysis = llm_service.detect_staleness_and_draft(old_doc, patch)

        new_doc_draft = analysis
        if "UPDATED_DOC:" in analysis:
            new_doc_draft = analysis.split("UPDATED_DOC:", 1)[1].strip()

        # Remove duplicate entries for the same file if they exist.
        pending_updates = [
            item for item in pending_updates if item["filename"] != filename
        ]
        pending_updates.append(
            {
                "filename": filename,
                "severity": flag.severity,
                "reason": flag.reason,
                "old_doc": old_doc,
                "new_doc_draft": new_doc_draft,
            }
        )
        db.save_queue(pending_updates)
        print(f"[QUEUE] Added {filename} to UI Review Queue.", flush=True)

    print(f"[DONE] Background task complete. Saved {len(pending_updates)} flags total.", flush=True)


@app.post("/webhook/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    print("[INFO] Webhook received from GitHub.", flush=True)
    if "commits" in payload:
        print("[INFO] Push event detected. Triggering AI analysis...", flush=True)
        background_tasks.add_task(process_webhook_commit)
    else:
        print(
            "[INFO] Webhook received, but it was not a code push (commits array missing).",
            flush=True,
        )
    return {"status": "Webhook received"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
