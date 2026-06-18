# AI Documentation Engine 📚🤖

An automated, AI-powered system designed to continuous-sync application
codebases with vector-based cloud documentation.

This engine listens to live repository changes via GitHub webhooks,
analyzes modified code snippets for documentation staleness using LLMs,
manages an automated review queue directly inside a vector database, and
exposes an interactive RAG (Retrieval-Augmented Generation) interface
for developers to query their documentation.

## 🚀 System Architecture & Pipeline

The system is deployed using a decoupled, production-grade microservices
architecture optimized for free-tier cloud constraints:

### The Ingestion Pipeline

-   Iterates through a target repository
    (`eCommerce-Backend_Springboot`)
-   Uses Groq LLMs to generate markdown manuals for each source file
-   Embeds generated documentation into Pinecone

### The Automated Listener (FastAPI on Render)

-   Listens for GitHub push webhooks
-   Parses code diffs
-   Runs staleness checks using LLMs
-   Pushes flagged updates into a cloud-hosted metadata queue

### The Human-In-The-Loop UI (Streamlit Cloud)

-   Interactive RAG chat interface
-   Dynamic review queue
-   Manual approval/dismissal of AI-generated documentation updates

## 🛠️ Tech Stack

  -----------------------------------------------------------------------
  Component               Technology              Role
  ----------------------- ----------------------- -----------------------
  Backend API             FastAPI, Uvicorn        Webhook listener and
                                                  background worker
                                                  orchestration

  Frontend UI             Streamlit               Chat interface and
                                                  review dashboard

  Vector Database         Pinecone (Serverless    Semantic storage and
                          AWS)                    synchronization

  AI Inference            Groq (Llama 3.3)        Documentation
                                                  generation and
                                                  staleness analysis

  VDB Embeddings          Pinecone Inference      Semantic vectorization

  Repository Access       PyGithub                Repository pulling and
                                                  diff tracking

  Containerization        Docker, Docker Compose  Local virtualization
  -----------------------------------------------------------------------

## 📂 Repository Structure

``` text
ai_doc_engine/
├── api/
│   └── main.py
├── ui/
│   └── app.py
├── engine/
│   ├── __init__.py
│   ├── github_service.py
│   ├── llm_service.py
│   └── rag_store.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── start.sh
```

## 🔑 Environment Configuration

``` env
GROQ_API_KEY=your_groq_api_key
GITHUB_TOKEN=your_github_personal_access_token
TARGET_REPO=YourGitHubUsername/eCommerce-Backend_Springboot
PINECONE_API_KEY=your_pinecone_api_key
```

## 💻 Local Development & Execution

``` bash
git clone https://github.com/YourGitHubUsername/ai_doc_engine.git
cd ai_doc_engine
docker compose up --build
```

-   Streamlit UI: http://localhost:8501
-   FastAPI Docs: http://localhost:8000/docs

## ☁️ Cloud Deployment Configuration

### 1. Webhook API Endpoint (Render)

-   Runtime: Docker Web Service
-   Runs `api/main.py` via `start.sh`
-   Exposes port 8000

### 2. Interactive Dashboard (Streamlit Community Cloud)

-   Deploys `ui/app.py`
-   Reads vector state directly from Pinecone

### 3. Centralized Cloud Queue State

Queue metadata is serialized as JSON and stored directly inside the
Pinecone index to provide consistent read/write behavior across Render
and Streamlit deployments.

---

# 📸 Screenshots

## 1. Streamlit Chat Interface

The RAG-powered chat interface allows developers to ask questions about the codebase using semantic search over the vector database.

<img width="1280" height="832" alt="Screenshot 2026-06-18 at 11 00 18 PM" src="https://github.com/user-attachments/assets/50a75e82-a9be-4eea-86f9-752c38449405" />


---

## 2. Documentation Review Queue

The review dashboard displays AI-generated documentation updates that require human approval before synchronization.

<img width="2560" height="1664" alt="image" src="https://github.com/user-attachments/assets/dfdd0307-969c-44cf-89e8-63cc7bd80758" />


---

## 3. Pinecone Vector Database Dashboard

The Pinecone index stores generated documentation embeddings along with queue metadata for synchronization across cloud services.

<img width="1280" height="832" alt="Screenshot 2026-06-18 at 11 26 26 PM" src="https://github.com/user-attachments/assets/6ff24074-e955-41c9-a2f8-8f55cece572f" />



---

# 🎥 Demo Workflow

1. Repository files are ingested and documented automatically.
2. Generated documentation is embedded into Pinecone.
3. GitHub push events trigger webhook notifications.
4. Modified files undergo LLM-based staleness analysis.
5. Flagged updates appear in the review queue.
6. Developers query the documentation through the RAG chat interface.
