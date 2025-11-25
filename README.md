🤖 Autonomous QA Agent: RAG-Powered Test Generation
🌟 Project Overview
The Autonomous QA Agent is a sophisticated, three-phase system designed to fully automate the creation of software testing artifacts—from test case generation to runnable Selenium scripts. It leverages a Retrieval-Augmented Generation (RAG) pipeline to ensure all generated assets are directly grounded in the provided project documentation and target HTML code.

The project demonstrates expertise in LLM orchestration, microservices using FastAPI, modern web development with Streamlit, and adherence to automation best practices.

💡 Architecture & Workflow
The system's core intelligence resides in the Python backend (backend.py), exposed via FastAPI endpoints, with the frontend (frontend.py) serving as the interactive control panel.

Phase 1: Knowledge Base Ingestion
This phase establishes the AI's memory. It fulfills the Content Parsing and Vector Database Ingestion requirements.

Multi-Format Loading: We process various document types (PDFs, Markdown, JSON, Text) using specialized LangChain Document Loaders.

Dual Grounding: We use BeautifulSoup to process the critical checkout.html file into two distinct memory items: the semantic text content and the raw HTML source code. This ensures the AI knows both what the page does and how it's built.

Indexing: The content is broken into contextual chunks using the RecursiveCharacterTextSplitter and indexed into the persistent Chroma DB, preserving metadata for traceability.

Phase 2: Test Case Generation
Here, the system converts a high-level requirement into a traceable, structured test plan using a RAG pipeline.

Retrieval (Semantic Search): The user's query is used to retrieve the most semantically relevant document chunks from the vector database.

Prompt Grounding: A carefully constructed Prompt Template is sent to Gemini 2.5 Pro. The prompt strictly mandates the output be "Based strictly on the provided context" (the Non-Hallucination Constraint) and forces a structured Markdown output format that includes the essential Grounded_Source column, proving the reasoning's validity.

Phase 3: Selenium Script Generation
This final phase translates a specific test scenario into high-quality, executable code.

Triple Grounding Prompt: This prompt is a masterful fusion of data: the selected Test Scenario, Contextual Rules retrieved dynamically from the DB, and the full Raw HTML Source.

Robust Code Mandate: The prompt demands adherence to automation best practices, specifying the use of webdriver.Chrome and demanding non-flaky elements like WebDriverWait (explicit waits). By including the HTML source, the LLM is guaranteed to use EXACT IDs/Selectors, overcoming a major obstacle in automated code generation.

🛠️ Technology Stack
The project relies on a strong set of modern libraries: Python, FastAPI, Streamlit, LangChain, Google Gemini 2.5 Pro, Chroma DB, and BeautifulSoup.

🚀 Getting Started
Prerequisites
Python 3.9+

API Key: A Google Gemini API Key (must be set as the GOOGLE_API_KEY environment variable in your project's .env file).

Installation
Clone the Repository:

git clone https://github.com/Nainsi-6/Autonomous-QA-Agent--Project.git
cd Autonomous-QA-Agent--Project
Set Up Environment and Install Dependencies:

python -m venv venv
.\venv\Scripts\activate  # Windows
pip install -r requirements.txt # Assuming requirements.txt exists
Running the Project
The backend and frontend must be run in separate terminal windows.

Start the Backend (FastAPI Service):

uvicorn backend:app --reload --host 0.0.0.0 --port 8000
Start the Frontend (Streamlit UI):


streamlit run frontend.py

Key Code Highlights-
backend.py: Contains the core logic for Dual Grounding, the RAG pipelines, and the Triple Grounding prompt strategy.

frontend.py: Manages user uploads, API communication, and dynamic rendering of the LLM's structured output.

chroma_db directory: Demonstrates persistence of the knowledge base.
