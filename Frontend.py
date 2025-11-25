import streamlit as st
import requests
import pandas as pd
import io

# Backend Configuration
BACKEND_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Autonomous QA Agent", 
    layout="wide", 
    page_icon="🤖",
    initial_sidebar_state="expanded"
)

st.title("🤖 Autonomous QA Agent")
st.markdown("### AI-Powered Test Case & Script Generation")

# Sidebar Navigation
with st.sidebar:
    st.header("📍 Navigation")
    mode = st.radio("Go to:", [
        "Phase 1: Knowledge Base", 
        "Phase 2: Test Generator", 
        "Phase 3: Script Generator"
    ])
    
    st.divider()
    st.caption("Backend Status")
    try:
        # Simple health check (optional, assumes backend is running)
        requests.get(f"{BACKEND_URL}/docs")
        st.success("Backend Online")
    except:
        st.error("Backend Offline")
        st.caption("Please run `python backend.py`")

# --- PHASE 1: INGESTION ---
if mode == "Phase 1: Knowledge Base":
    st.header("📚 Phase 1: Ingestion")
    st.markdown("Build the 'Testing Brain' by uploading project assets.")
    
    with st.expander("ℹ️ How to use this phase"):
        st.write("""
        1. **Support Docs:** Upload PDF, MD, or TXT files describing the product specs.
        2. **Target HTML:** Upload the specific `checkout.html` you want to test.
        3. Click **Build Knowledge Base** to parse files and create vector embeddings.
        """)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("1. Upload Documentation")
        uploaded_docs = st.file_uploader(
            "Specs, Guidelines, APIs (PDF/MD/TXT)", 
            accept_multiple_files=True,
            type=['md', 'txt', 'json', 'pdf']
        )
    with col2:
        st.subheader("2. Upload Target App")
        uploaded_html = st.file_uploader(
            "Web Page (HTML)", 
            type=['html']
        )

    if st.button("🚀 Build Knowledge Base", type="primary", use_container_width=True):
        if uploaded_docs and uploaded_html:
            # Use status container for better UX
            with st.status("Ingesting Data...", expanded=True) as status:
                try:
                    # Prepare payload
                    st.write("📂 Preparing files...")
                    files_payload = [('files', (doc.name, doc.getvalue(), doc.type)) for doc in uploaded_docs]
                    html_payload = ('html_file', (uploaded_html.name, uploaded_html.getvalue(), uploaded_html.type))
                    
                    st.write("🧠 Generating Embeddings & Vectors...")
                    response = requests.post(f"{BACKEND_URL}/build-knowledge-base", files=files_payload + [html_payload])
                    
                    if response.status_code == 200:
                        data = response.json()
                        status.update(label="Knowledge Base Ready!", state="complete", expanded=False)
                        st.success(f"✅ Success! Ingested {len(uploaded_docs) + 1} files.")
                        st.metric("Vector Chunks Created", data['chunks_created'])
                    else:
                        status.update(label="Error Occurred", state="error")
                        st.error(f"Backend Error: {response.text}")
                except Exception as e:
                    status.update(label="Connection Failed", state="error")
                    st.error(f"Failed to connect to backend: {e}")
        else:
            st.warning("⚠️ Please upload ALL required files before building.")

# --- PHASE 2: TEST CASE GENERATION ---
elif mode == "Phase 2: Test Generator":
    st.header("🧪 Phase 2: Test Case Generation")
    
    with st.expander("ℹ️ How to use this phase"):
        st.write("Describe what you want to test. The Agent will retrieve rules from the Knowledge Base and generate a structured Test Plan.")

    user_query = st.text_area(
        "Enter Test Requirement:", 
        value="Generate all positive and negative test cases for the discount code feature.",
        height=100,
        placeholder="E.g., Test the payment form validation..."
    )

    if st.button("⚡ Generate Test Plan", type="primary"):
        if user_query:
            with st.spinner("🤖 Consulting Knowledge Base & Gemini Pro..."):
                try:
                    payload = {"prompt": user_query}
                    response = requests.post(f"{BACKEND_URL}/generate-test-cases", json=payload)
                    
                    if response.status_code == 200:
                        data = response.json()
                        st.subheader("📝 Generated Test Plan")
                        st.markdown(data['test_plan'])
                        
                        # Save to session state for Phase 3
                        st.session_state['last_test_plan'] = data['test_plan']
                        st.toast("Test Plan Saved! Proceed to Phase 3.", icon="✅")
                    else:
                        st.error(f"Error {response.status_code}: {response.text}")
                except Exception as e:
                    st.error(f"Connection Error: {e}")

# --- PHASE 3: SELENIUM SCRIPT GENERATION ---
elif mode == "Phase 3: Script Generator":
    st.header("💻 Phase 3: Selenium Script Generation")
    
    with st.expander("ℹ️ How to use this phase"):
        st.write("1. Select the test cases you want to automate using the checkboxes below.")
        st.write("2. Click **Generate Scripts** to create Selenium code for all selected cases.")
        st.write("3. Alternatively, use the 'Manual Mode' to paste a custom scenario.")

    # Check if we have a test plan in memory
    if 'last_test_plan' in st.session_state and st.session_state['last_test_plan']:
        st.subheader("Select Test Cases to Automate")
        
        raw_plan = st.session_state['last_test_plan']
        
        # --- PARSING LOGIC: Convert Markdown Table to DataFrame ---
        rows = []
        try:
            lines = raw_plan.strip().split('\n')
            # Look for table structure (lines starting with |)
            table_lines = [line for line in lines if line.strip().startswith("|")]
            
            # Simple parsing of markdown table
            for line in table_lines:
                # Remove outer pipes and split
                cells = [c.strip() for c in line.strip('|').split('|')]
                
                # Skip separator lines (e.g. ---|---|---) and header lines if we are iterating
                if "---" in cells[0] or "Test_ID" in cells[0]:
                    continue
                
                # Ensure we have enough columns (Test_ID, Feature, Scenario, Expected_Result, Source)
                if len(cells) >= 4: 
                    # Handle potential variations in column count gracefully
                    row_data = {
                        "Test_ID": cells[0],
                        "Feature": cells[1] if len(cells) > 1 else "",
                        "Scenario": cells[2] if len(cells) > 2 else "",
                        "Expected_Result": cells[3] if len(cells) > 3 else "",
                        "Grounded_Source": cells[4] if len(cells) > 4 else ""
                    }
                    rows.append(row_data)
        except Exception as e:
            st.warning(f"Could not automatically parse the table structure. Please use Manual Mode. Error: {e}")

        if rows:
            df = pd.DataFrame(rows)
            # Add a 'Select' column for checkboxes, defaulted to False
            df.insert(0, "Select", False)
            
            # Display interactive table
            edited_df = st.data_editor(
                df,
                column_config={
                    "Select": st.column_config.CheckboxColumn(
                        "Generate?",
                        help="Select this test case for script generation",
                        default=False,
                    )
                },
                disabled=["Test_ID", "Feature", "Scenario", "Expected_Result", "Grounded_Source"],
                hide_index=True,
                use_container_width=True
            )
            
            # Filter for selected rows
            selected_cases = edited_df[edited_df.Select]
            
            if st.button(f"🤖 Generate Scripts for ({len(selected_cases)}) Selected Cases", type="primary"):
                if not selected_cases.empty:
                    progress_bar = st.progress(0)
                    total = len(selected_cases)
                    
                    for i, (index, row) in enumerate(selected_cases.iterrows()):
                        # Construct a clean string for the backend
                        test_case_str = (
                            f"Test_ID: {row['Test_ID']}\n"
                            f"Feature: {row['Feature']}\n"
                            f"Scenario: {row['Scenario']}\n"
                            f"Expected_Result: {row['Expected_Result']}\n"
                            f"Source: {row['Grounded_Source']}"
                        )
                        
                        with st.expander(f"🐍 Script: {row['Test_ID']} - {row['Scenario']}", expanded=True):
                            with st.spinner(f"Generating code for {row['Test_ID']}..."):
                                try:
                                    payload = {"test_case": test_case_str}
                                    response = requests.post(f"{BACKEND_URL}/generate-selenium-script", json=payload)
                                    
                                    if response.status_code == 200:
                                        data = response.json()
                                        script_code = data['script']
                                        
                                        # Clean up markdown
                                        if script_code.startswith("```python"):
                                            script_code = script_code.replace("```python", "").replace("```", "")
                                        
                                        st.code(script_code, language='python')
                                    else:
                                        st.error(f"Error: {response.text}")
                                except Exception as e:
                                    st.error(f"Connection Error: {e}")
                        
                        progress_bar.progress((i + 1) / total)
                else:
                    st.warning("Please select at least one test case from the table.")
        else:
            st.info("No parseable table found in the Test Plan. Use Manual Mode below.")
            with st.expander("View Raw Plan"):
                st.markdown(raw_plan)

    else:
        st.info("ℹ️ No test plan found. Please go to Phase 2 to generate one.")

    # Fallback / Manual Mode
    st.divider()
    with st.expander("Manual Mode (Paste Single Scenario)"):
        test_case_input = st.text_area(
            "Paste Specific Test Scenario:",
            height=150,
            placeholder="Test_ID: TC-001\nScenario: Apply valid code 'SAVE15'\nExpected: Price reduces by 15%"
        )
        if st.button("Generate Script (Manual)", type="secondary"):
            if test_case_input:
                with st.spinner("Generating..."):
                    try:
                        payload = {"test_case": test_case_input}
                        response = requests.post(f"{BACKEND_URL}/generate-selenium-script", json=payload)
                        if response.status_code == 200:
                            data = response.json()
                            script_code = data['script']
                            if script_code.startswith("```python"):
                                script_code = script_code.replace("```python", "").replace("```", "")
                            st.code(script_code, language='python')
                        else:
                            st.error(f"Error: {response.text}")
                    except Exception as e:
                        st.error(f"Connection Error: {e}")