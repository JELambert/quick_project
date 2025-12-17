import streamlit as st
import pandas as pd
from openai import OpenAI
from docx import Document
import os
from dotenv import load_dotenv
import io

# Load environment variables
load_dotenv()

# ===== CONFIGURATION =====
def get_openai_client():
    """Get OpenAI client with API key from secrets or .env"""
    try:
        # Try Streamlit secrets first (for cloud deployment)
        api_key = st.secrets.get("OPENAI_API_KEY")
    except:
        # Fall back to .env (for local development)
        api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        st.error("OpenAI API key not found. Please set OPENAI_API_KEY in .env or Streamlit secrets.")
        st.stop()

    return OpenAI(api_key=api_key)

# ===== DATA PROCESSING FUNCTIONS =====

@st.cache_data
def parse_task_list(file_path):
    """Parse Task List document to extract Q&A examples"""
    try:
        doc = Document(file_path)

        # Extract text from document
        questions = []
        responses = []
        todos = []

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue

            # Simple heuristic: questions often end with ?
            if '?' in text:
                questions.append(text)

            # Could check for font color, but python-docx color detection is complex
            # For POC, just extract all meaningful text as examples

        # Format as few-shot examples
        example_text = "Example questions from past analysis:\n"
        for i, q in enumerate(questions[:5], 1):  # First 5 questions as examples
            example_text += f"\n{i}. {q}"

        return example_text
    except Exception as e:
        st.warning(f"Could not parse Task List: {e}")
        return "No Task List examples available."

def load_excel_data(file_path_or_buffer, file_name=""):
    """Load and summarize Excel data"""
    try:
        # Read all sheets
        excel_file = pd.ExcelFile(file_path_or_buffer)
        data_summary = {}

        st.info(f"Loading {file_name}: Found {len(excel_file.sheet_names)} sheets")

        for sheet_name in excel_file.sheet_names:
            try:
                df = pd.read_excel(file_path_or_buffer, sheet_name=sheet_name)

                # Create summary for this sheet
                summary = f"\n### Sheet: {sheet_name}\n"
                summary += f"- Rows: {len(df)}\n"
                summary += f"- Columns: {len(df.columns)}\n"
                summary += f"- Column Names: {', '.join(df.columns.tolist())}\n"

                # Add sample data (first 10 rows)
                summary += f"\n**Sample Data (first 10 rows):**\n"
                summary += df.head(10).to_markdown(index=False)

                # Add basic stats for numeric columns
                numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
                if numeric_cols:
                    summary += f"\n\n**Numeric Column Statistics:**\n"
                    for col in numeric_cols[:5]:  # First 5 numeric columns
                        summary += f"- {col}: min={df[col].min():.2f}, max={df[col].max():.2f}, mean={df[col].mean():.2f}\n"

                data_summary[sheet_name] = summary
            except Exception as sheet_error:
                st.warning(f"Could not load sheet '{sheet_name}': {sheet_error}")
                continue

        st.success(f"Successfully loaded {len(data_summary)} sheets from {file_name}")
        return data_summary
    except Exception as e:
        st.error(f"Error loading Excel file '{file_name}': {e}")
        import traceback
        st.error(f"Traceback: {traceback.format_exc()}")
        return {}

def create_data_context(data_summary):
    """Create concise data context for LLM"""
    if not data_summary:
        return "No data loaded."

    context = "\n# Available Data\n"
    for sheet_name, summary in data_summary.items():
        context += summary + "\n"

    return context

# ===== CHAT LOGIC =====

def build_system_prompt(task_examples, data_context):
    """Build system prompt with examples and data context"""
    prompt = """You are a financial analyst assistant specializing in analyzing general ledger transactions and balance sheet data.

Your role is to:
1. Analyze transaction-level data to identify patterns, anomalies, and insights
2. Answer questions about the financial data
3. Generate data-driven questions for management discussions
4. Help interpret financial information for due diligence purposes

{task_examples}

When analyzing data:
- Be specific and reference actual numbers from the data
- Identify unusual transactions or patterns
- Suggest areas requiring clarification from management
- Format responses clearly with bullet points and sections

{data_context}
"""

    return prompt.format(task_examples=task_examples, data_context=data_context)

def stream_openai_response(client, messages):
    """Stream response from OpenAI API"""
    try:
        stream = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            stream=True,
            temperature=0.7,
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception as e:
        yield f"\n\nError: {str(e)}"

# ===== STREAMLIT UI =====

def initialize_session_state():
    """Initialize session state variables"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "data_summary" not in st.session_state:
        st.session_state.data_summary = {}
    if "task_examples" not in st.session_state:
        st.session_state.task_examples = ""
    if "data_loaded" not in st.session_state:
        st.session_state.data_loaded = False

def main():
    st.set_page_config(page_title="Financial Analysis Assistant", page_icon="💼", layout="wide")

    initialize_session_state()

    # Get OpenAI client
    client = get_openai_client()

    # ===== SIDEBAR =====
    with st.sidebar:
        st.title("📊 Data Source")

        # Mode selection
        mode = st.radio("Select Mode:", ["Use Existing Files", "Upload New Files"])

        st.divider()

        # Handle data loading based on mode
        if mode == "Use Existing Files":
            st.info("Using files from repository")

            # Load Task List
            task_list_path = "Task List.docx"
            if os.path.exists(task_list_path) and not st.session_state.task_examples:
                st.session_state.task_examples = parse_task_list(task_list_path)

            # Load GL Transactions
            gl_path = "Balance_Sheet_GL_Transactions (1).xlsx"
            databook_path = "Example Databook Output.xlsx"

            if st.button("Load Repository Files", type="primary"):
                with st.spinner("Loading files..."):
                    # Reset data summary
                    st.session_state.data_summary = {}

                    # Load GL Transactions
                    if os.path.exists(gl_path):
                        gl_data = load_excel_data(gl_path, "GL Transactions")
                        st.write(f"DEBUG: GL data has {len(gl_data)} sheets")
                        st.session_state.data_summary.update(gl_data)
                    else:
                        st.error(f"File not found: {gl_path}")

                    # Load Databook
                    if os.path.exists(databook_path):
                        databook_data = load_excel_data(databook_path, "Databook")
                        st.write(f"DEBUG: Databook data has {len(databook_data)} sheets")
                        st.session_state.data_summary.update(databook_data)
                    else:
                        st.error(f"File not found: {databook_path}")

                    st.write(f"DEBUG: Total sheets in session state: {len(st.session_state.data_summary)}")
                    st.session_state.data_loaded = True
                    st.success(f"Files loaded successfully! Total sheets: {len(st.session_state.data_summary)}")
                    st.rerun()

        else:  # Upload mode
            st.info("Upload your own Excel files")

            # Task list upload
            task_file = st.file_uploader("Upload Task List (optional)", type=['docx'])
            if task_file:
                st.session_state.task_examples = parse_task_list(task_file)

            # Excel upload
            excel_files = st.file_uploader(
                "Upload Excel Files",
                type=['xlsx', 'xls'],
                accept_multiple_files=True
            )

            if excel_files:
                if st.button("Process Uploaded Files", type="primary"):
                    with st.spinner("Processing files..."):
                        st.session_state.data_summary = {}
                        for uploaded_file in excel_files:
                            # Read file into bytes
                            file_data = io.BytesIO(uploaded_file.getvalue())
                            st.write(f"Processing: {uploaded_file.name}")
                            file_summary = load_excel_data(file_data, uploaded_file.name)
                            st.write(f"DEBUG: {uploaded_file.name} has {len(file_summary)} sheets")
                            st.session_state.data_summary.update(file_summary)

                        st.write(f"DEBUG: Total sheets in session state: {len(st.session_state.data_summary)}")
                        st.session_state.data_loaded = True
                        st.session_state.messages = []  # Clear chat history for new data
                        st.success(f"Processed {len(excel_files)} file(s)! Total sheets: {len(st.session_state.data_summary)}")
                        st.rerun()

        # Display data status
        st.divider()
        st.subheader("Data Status")
        if st.session_state.data_loaded:
            st.success(f"✅ Data loaded: {len(st.session_state.data_summary)} sheets")
            if len(st.session_state.data_summary) > 0:
                with st.expander("View loaded sheets"):
                    for sheet_name in st.session_state.data_summary.keys():
                        st.write(f"- {sheet_name}")
            else:
                st.error("⚠️ Data marked as loaded but no sheets found!")
        else:
            st.warning("⚠️ No data loaded yet")

        # Debug info
        with st.expander("Debug Info"):
            st.write(f"data_loaded: {st.session_state.data_loaded}")
            st.write(f"data_summary type: {type(st.session_state.data_summary)}")
            st.write(f"data_summary keys: {list(st.session_state.data_summary.keys())}")
            st.write(f"Number of sheets: {len(st.session_state.data_summary)}")

        # Clear chat button
        if st.button("Clear Chat History"):
            st.session_state.messages = []
            st.rerun()

    # ===== MAIN CHAT AREA =====
    st.title("💼 Financial Analysis Assistant")

    if not st.session_state.data_loaded:
        st.info("👈 Please load data from the sidebar to begin analysis")
        st.markdown("""
        ### Getting Started
        1. Choose a mode: Use existing repository files or upload your own
        2. Load the data
        3. Start asking questions or run deep research analysis

        ### What You Can Do
        - Ask questions about the financial data
        - Request specific analyses or breakdowns
        - Generate management questions based on data insights
        - Run automated deep research analysis
        """)
        return

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Deep Research button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔍 Run Deep Research Analysis", use_container_width=True, type="secondary"):
            # Create research prompt
            research_prompt = """Perform a comprehensive analysis of the available financial data. Please:

1. **Data Overview**: Summarize what data is available and the time period covered

2. **Key Insights**: Identify the most important findings, trends, and patterns in the data

3. **Anomalies & Red Flags**: Point out any unusual transactions, inconsistencies, or areas of concern

4. **Deep Dive Areas**: Highlight specific accounts, transactions, or categories that warrant deeper investigation

5. **Management Questions**: Generate a list of specific, data-driven questions for the management team (similar to the Task List format). Each question should reference specific data points.

Be thorough and specific, citing actual numbers and examples from the data."""

            # Add to messages
            st.session_state.messages.append({"role": "user", "content": "🔍 Running Deep Research Analysis..."})

            # Display user message
            with st.chat_message("user"):
                st.markdown("🔍 Running Deep Research Analysis...")

            # Generate response
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = ""

                # Build messages for API
                data_context = create_data_context(st.session_state.data_summary)
                system_prompt = build_system_prompt(st.session_state.task_examples, data_context)

                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": research_prompt}
                ]

                # Stream response
                for chunk in stream_openai_response(client, messages):
                    full_response += chunk
                    message_placeholder.markdown(full_response + "▌")

                message_placeholder.markdown(full_response)

            # Add assistant response to history
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            st.rerun()

    # Chat input
    if prompt := st.chat_input("Ask a question about the data..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""

            # Build messages for API
            data_context = create_data_context(st.session_state.data_summary)
            system_prompt = build_system_prompt(st.session_state.task_examples, data_context)

            messages = [{"role": "system", "content": system_prompt}]

            # Add chat history
            for msg in st.session_state.messages[:-1]:  # Exclude the last user message we just added
                messages.append({"role": msg["role"], "content": msg["content"]})

            # Add current user message
            messages.append({"role": "user", "content": prompt})

            # Stream response
            for chunk in stream_openai_response(client, messages):
                full_response += chunk
                message_placeholder.markdown(full_response + "▌")

            message_placeholder.markdown(full_response)

        # Add assistant response to history
        st.session_state.messages.append({"role": "assistant", "content": full_response})
        st.rerun()

if __name__ == "__main__":
    main()
