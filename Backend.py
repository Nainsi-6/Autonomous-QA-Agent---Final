import os
# Suppress TensorFlow informational logs and enforce consistent operation
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List
import uvicorn
from dotenv import load_dotenv

# --- Modern LangChain Imports ---
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv()

app = FastAPI(title="QA Agent Backend")

# --- Configuration ---
VECTOR_DB_DIR = "./chroma_db"
UPLOAD_DIR = "./uploaded_docs"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(VECTOR_DB_DIR, exist_ok=True)

# 1. Initialize Embeddings
# Using local model to avoid extra API costs/latency
embedding_function = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# 2. Initialize Vector DB
vector_db = Chroma(
    persist_directory=VECTOR_DB_DIR,
    embedding_function=embedding_function,
    collection_name="qa_knowledge_base"
)

# 3. Initialize LLM (Gemini 1.5 Pro)
api_key = os.getenv("GOOGLE_API_KEY")
llm = None

if api_key:
    try:
        # gemini-1.5-pro is recommended for complex reasoning tasks like coding
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-pro", 
            temperature=0.1, # Low temperature for consistent code generation
            convert_system_message_to_human=True,
            google_api_key=api_key
        )
    except Exception as e:
        print(f"Error initializing Gemini: {e}")

# --- Data Models ---
class TestGenerationRequest(BaseModel):
    prompt: str

class ScriptGenerationRequest(BaseModel):
    test_case: str

# --- Helper Functions ---
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

def process_html_file(file_path: str) -> List[Document]:
    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
    
    # Store both clean text (for logic) and raw HTML (for structure)
    return [
        Document(page_content=soup.get_text(separator="\n"), metadata={"source": "checkout.html", "type": "text"}),
        Document(page_content=str(soup), metadata={"source": "checkout.html", "type": "code"})
    ]

def load_document(file_path: str, filename: str) -> List[Document]:
    """Loads support documents based on file extension."""
    if filename.lower().endswith(".pdf"):
        # Explicit PDF support (Assignment Phase 1)
        loader = PyPDFLoader(file_path)
    else:
        # Fallback to TextLoader for MD, TXT, JSON
        loader = TextLoader(file_path, encoding="utf-8")
    return loader.load()

# --- Endpoints ---

@app.post("/build-knowledge-base")
async def build_knowledge_base(
    files: List[UploadFile] = File(...),
    html_file: UploadFile = File(...)
):
    """Phase 1: Ingests documents into Vector DB."""
    documents = []
    
    # 1. Process Support Docs
    for file in files:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        try:
            documents.extend(load_document(file_path, file.filename))
        except Exception as e:
            print(f"Skipping {file.filename}: {e}")

    # 2. Process HTML
    html_path = os.path.join(UPLOAD_DIR, "checkout.html")
    with open(html_path, "wb") as buffer:
        shutil.copyfileobj(html_file.file, buffer)
    documents.extend(process_html_file(html_path))

    # 3. Chunking & Storage
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunked_docs = text_splitter.split_documents(documents)
    
    if chunked_docs:
        vector_db.add_documents(chunked_docs)

    return {"status": "success", "message": f"Processed {len(files) + 1} files.", "chunks_created": len(chunked_docs)}

@app.post("/generate-test-cases")
async def generate_test_cases(request: TestGenerationRequest):
    """Phase 2: Generate Test Cases."""
    if not llm:
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY not configured.")

    # Retrieve relevant documentation
    retriever = vector_db.as_retriever(search_kwargs={"k": 5})

    template = """
    You are an expert QA Automation Engineer.
    Based strictly on the provided context, generate detailed test cases.
    
    Context: {context}
    User Request: {question}
    
    Requirements:
    1. Do NOT hallucinate. Use only the provided context.
    2. Output a Markdown table with columns: Test_ID, Feature, Scenario, Expected_Result, Grounded_Source.
    """
    prompt = PromptTemplate.from_template(template)

    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    
    try:
        result = rag_chain.invoke(request.prompt)
        return {"status": "success", "test_plan": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-selenium-script")
async def generate_selenium_script(request: ScriptGenerationRequest):
    """Phase 3: Generate Selenium Script."""
    if not llm:
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY not configured.")
        
    html_path = os.path.join(UPLOAD_DIR, "checkout.html")
    if not os.path.exists(html_path):
        raise HTTPException(status_code=404, detail="checkout.html not found. Please run /build-knowledge-base first.")
    
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # 1. Retrieve relevant documentation snippets from Vector DB
    # (Assignment Requirement: "Retrieve relevant documentation snippets from the vector DB")
    relevant_docs = vector_db.similarity_search(request.test_case, k=3)
    context_rules = "\n".join([doc.page_content for doc in relevant_docs])

    # 2. Construct Prompt (Grounding in HTML + Rules)
    prompt = f"""
    Role: Senior Selenium Automation Engineer.
    Task: Write a robust, runnable Python Selenium script for this test case.
    
    Test Case Scenario: 
    {request.test_case}
    
    Relevant Rules (Grounding):
    {context_rules}
    
    Target HTML Source (Use EXACT IDs/Selectors):
    {html_content}
    
    Requirements:
    1. Use `webdriver.Chrome`.
    2. Use `WebDriverWait` for explicit waits.
    3. Assert the 'Expected Result' mentioned in the test case.
    4. Handle the 'checkout.html' file path assuming it is in the current directory.
    5. Output ONLY valid Python code.
    """

    try:
        response = llm.invoke(prompt)
        return {"status": "success", "script": response.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)