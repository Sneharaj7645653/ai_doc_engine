#!/bin/bash
# 1. Start the FastAPI backend in the background
uvicorn api.main:app --host 0.0.0.0 --port 8000 &

# 2. Start the Streamlit UI in the foreground
streamlit run ui/app.py --server.port 8501 --server.address 0.0.0.0