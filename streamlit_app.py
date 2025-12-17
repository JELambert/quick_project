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

def create_smart_summary(df, sheet_name):
    """Create intelligent summary based on sheet type"""
    summary = f"\n### Sheet: {sheet_name}\n"
    summary += f"- Rows: {len(df)}\n"
    summary += f"- Columns: {len(df.columns)}\n"
    summary += f"- Column Names: {', '.join(df.columns.tolist())}\n"

    # Check if this is transaction-level data (GL Detail)
    is_gl_detail = 'GL Detail' in sheet_name or len(df) > 1000

    # Find key columns
    date_cols = [col for col in df.columns if 'date' in col.lower() or 'year' in col.lower()]
    amount_cols = [col for col in df.columns if 'amount' in col.lower() or 'debit' in col.lower() or 'credit' in col.lower()]
    account_cols = [col for col in df.columns if 'account' in col.lower() or 'description' in col.lower() or 'name' in col.lower()]
    vendor_cols = [col for col in df.columns if 'vendor' in col.lower() or 'customer' in col.lower()]

    if is_gl_detail and amount_cols:
        # For transaction data, provide aggregations
        summary += f"\n**Transaction Analysis (from {len(df):,} transactions):**\n"

        # Year-based analysis
        year_col = None
        if 'Year' in df.columns:
            year_col = 'Year'
        elif date_cols:
            date_col = date_cols[0]
            try:
                df['Parsed_Year'] = pd.to_datetime(df[date_col], errors='coerce').dt.year
                year_col = 'Parsed_Year'
            except Exception as e:
                pass

        if year_col and year_col in df.columns:
            try:
                # Aggregate by year
                year_summary = df.groupby(year_col)[amount_cols[0]].sum().sort_index()
                summary += f"\n**Total by Year:**\n"
                for year, total in year_summary.items():
                    if pd.notna(year) and year > 2000 and year < 2030:  # Filter to realistic years
                        summary += f"- {int(year)}: ${total:,.2f}\n"
            except Exception as e:
                pass

        # Account-level breakdown with year comparison
        if account_cols and year_col:
            account_col = account_cols[0]
            try:
                # Get top accounts by amount
                top_accounts = df.groupby(account_col)[amount_cols[0]].sum().abs().sort_values(ascending=False).head(15)
                summary += f"\n**Top 15 Accounts by Amount:**\n"
                for account, total in top_accounts.items():
                    summary += f"- {account}: ${total:,.2f}\n"

                # Year-over-year comparison for top expense accounts
                # Look for subcontractor/expense-related accounts
                expense_keywords = ['subcontract', 'expense', '5000', 'cost', 'vendor']
                expense_accounts = [acc for acc in top_accounts.index if any(kw in str(acc).lower() for kw in expense_keywords)]

                if expense_accounts and len(expense_accounts) > 0:
                    summary += f"\n**Year-over-Year Analysis (Key Expense Accounts):**\n"
                    for account in expense_accounts[:5]:  # Top 5 expense accounts
                        year_data = df[df[account_col] == account].groupby(year_col)[amount_cols[0]].sum().abs()
                        if len(year_data) > 1:
                            summary += f"\n{account}:\n"
                            for year, amount in year_data.sort_index().items():
                                if pd.notna(year) and year > 2000 and year < 2030:
                                    summary += f"  - {int(year)}: ${amount:,.2f}\n"
            except Exception as e:
                pass

        # Project-level analysis
        project_cols = [col for col in df.columns if 'project' in col.lower()]
        if project_cols:
            project_col = project_cols[0]
            try:
                top_projects = df.groupby(project_col)[amount_cols[0]].sum().abs().sort_values(ascending=False).head(10)
                summary += f"\n**Top 10 Projects by Amount:**\n"
                for project, total in top_projects.items():
                    if pd.notna(project) and str(project) != 'nan' and project != 0:
                        summary += f"- {project}: ${total:,.2f}\n"
            except Exception as e:
                pass

        # Description-based analysis (look for work types)
        desc_cols = [col for col in df.columns if 'description' in col.lower() or 'gl_description' in col.lower()]
        if desc_cols:
            desc_col = desc_cols[0]
            try:
                # Look for key work types (sprinkler, HVAC, electrical, etc.)
                work_types = ['sprinkler', 'hvac', 'electrical', 'plumbing', 'concrete', 'roofing']
                summary += f"\n**Work Type Analysis:**\n"
                for work_type in work_types:
                    work_data = df[df[desc_col].astype(str).str.contains(work_type, case=False, na=False)]
                    if len(work_data) > 0:
                        total = work_data[amount_cols[0]].abs().sum()
                        if total > 1000:  # Only show if significant
                            summary += f"- {work_type.title()}: ${total:,.2f} ({len(work_data)} transactions)\n"
            except Exception as e:
                pass

        # Revenue pattern analysis (temporal patterns for revenue accounts)
        if account_cols and year_col:
            account_col = account_cols[0]
            try:
                # Identify revenue accounts (typically 4000-series)
                revenue_accounts = [acc for acc in df[account_col].unique()
                                   if pd.notna(acc) and ('4000' in str(acc) or 'revenue' in str(acc).lower())]

                if revenue_accounts:
                    summary += f"\n**Revenue Pattern Analysis:**\n"

                    # Get month column if available
                    month_cols = [col for col in df.columns if 'month' in col.lower()]

                    for acc in revenue_accounts[:5]:  # Top 5 revenue accounts
                        acc_data = df[df[account_col] == acc]
                        if len(acc_data) < 2:
                            continue

                        # Analyze transaction frequency
                        if month_cols:
                            month_col = month_cols[0]
                            try:
                                # Convert month to datetime if needed
                                acc_data_copy = acc_data.copy()
                                acc_data_copy['month_dt'] = pd.to_datetime(acc_data_copy[month_col], errors='coerce')
                                acc_data_copy['year_month'] = acc_data_copy['month_dt'].dt.to_period('M')
                                acc_data_copy['quarter'] = acc_data_copy['month_dt'].dt.quarter

                                # Count transactions per month and quarter
                                monthly_txns = acc_data_copy.groupby('year_month').size()
                                quarterly_txns = acc_data_copy.groupby([year_col, 'quarter']).size()

                                # Detect pattern
                                pattern = "Unknown"
                                months_with_txns = set(acc_data_copy['month_dt'].dt.month.dropna())

                                # Check for quarterly pattern (transactions in specific months like 3,6,9,12)
                                quarterly_months = {3, 6, 9, 12}
                                if months_with_txns and months_with_txns.issubset(quarterly_months):
                                    pattern = "Quarterly (Q-end)"
                                elif len(monthly_txns) > 0 and monthly_txns.mean() >= 0.8:
                                    pattern = "Monthly"
                                elif len(quarterly_txns) > 0:
                                    avg_per_quarter = quarterly_txns.mean()
                                    if avg_per_quarter < 5:
                                        pattern = "Quarterly"

                                # Calculate total revenue
                                total_rev = acc_data[amount_cols[0]].abs().sum()

                                summary += f"\n{acc}:\n"
                                summary += f"  - Total Revenue: ${total_rev:,.2f}\n"
                                summary += f"  - Pattern: {pattern}\n"
                                summary += f"  - Transaction Count: {len(acc_data)}\n"

                                # Add management question hint for quarterly patterns
                                if "Quarterly" in pattern:
                                    summary += f"  - ⚠️ Management Question: Is this pre-billed? May require deferred revenue accounting.\n"

                            except Exception as e:
                                pass

            except Exception as e:
                pass

        # Vendor/Customer breakdown
        if vendor_cols and len(vendor_cols) > 0:
            vendor_col = vendor_cols[0]
            try:
                top_vendors = df.groupby(vendor_col)[amount_cols[0]].sum().abs().sort_values(ascending=False).head(10)
                summary += f"\n**Top 10 by {vendor_col}:**\n"
                for vendor, total in top_vendors.items():
                    if pd.notna(vendor) and vendor != '':
                        summary += f"- {vendor}: ${total:,.2f}\n"
            except Exception as e:
                pass

        # Sample transactions from different years
        summary += f"\n**Sample Transactions:**\n"
        if 'Year' in df.columns:
            # Get samples from 2024 and 2023
            for year in sorted(df['Year'].dropna().unique(), reverse=True)[:2]:
                year_data = df[df['Year'] == year].head(3)
                if len(year_data) > 0:
                    summary += f"\n*{int(year)} samples:*\n"
                    summary += year_data[[col for col in df.columns if col != 'Year']].head(3).to_markdown(index=False)
                    summary += "\n"
        else:
            # Just show first few rows
            summary += df.head(5).to_markdown(index=False)
    else:
        # For summary sheets, show more rows
        summary += f"\n**Data:**\n"
        summary += df.head(10).to_markdown(index=False)

        # Add basic stats
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        if numeric_cols:
            summary += f"\n\n**Key Statistics:**\n"
            for col in numeric_cols[:3]:
                summary += f"- {col}: min={df[col].min():.2f}, max={df[col].max():.2f}, mean={df[col].mean():.2f}\n"

    return summary

def load_excel_data(file_path_or_buffer, file_name=""):
    """Load and summarize Excel data with intelligent aggregations"""
    try:
        # Read all sheets
        excel_file = pd.ExcelFile(file_path_or_buffer)
        data_summary = {}

        st.info(f"Loading {file_name}: Found {len(excel_file.sheet_names)} sheets")

        for sheet_name in excel_file.sheet_names:
            try:
                df = pd.read_excel(file_path_or_buffer, sheet_name=sheet_name)

                # Skip empty sheets
                if len(df) == 0:
                    continue

                # Create smart summary based on data type
                summary = create_smart_summary(df, sheet_name)
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

def create_data_context(data_summary, selected_sheets=None):
    """Create concise data context for LLM - only includes selected sheets"""
    if not data_summary:
        return "No data loaded."

    # If selected_sheets is provided, filter to only those
    if selected_sheets:
        filtered_summary = {k: v for k, v in data_summary.items() if k in selected_sheets}
    else:
        filtered_summary = data_summary

    if not filtered_summary:
        return "No sheets selected for analysis."

    context = f"\n# Available Data ({len(filtered_summary)} sheets)\n"
    for sheet_name, summary in filtered_summary.items():
        context += summary + "\n"

    return context

# ===== CHAT LOGIC =====

def build_system_prompt(task_examples, data_context):
    """Build system prompt with examples and data context"""
    prompt = """You are a financial analyst assistant specializing in analyzing general ledger transactions and balance sheet data.

IMPORTANT: The complete financial data is provided below in this message. You have DIRECT ACCESS to this data. You can and should reference specific numbers, transactions, accounts, and values from the data provided. DO NOT say you cannot access the data - it is right here in your context.

Your role is to:
1. Analyze the transaction-level data provided below to identify patterns, anomalies, and insights
2. Answer questions about the financial data by referencing the specific values shown
3. Generate data-driven questions for management discussions based on what you see in the data
4. Help interpret financial information for due diligence purposes

{task_examples}

When analyzing data:
- Reference specific numbers, accounts, and values from the data tables below
- Identify unusual transactions or patterns you observe in the data
- Cite specific examples from the sample rows provided
- Calculate totals, averages, or trends from the statistics shown
- Suggest areas requiring clarification based on what you see in the data
- Format responses clearly with bullet points and sections

===== FINANCIAL DATA (YOU HAVE FULL ACCESS TO THIS DATA) =====
{data_context}
===== END OF FINANCIAL DATA =====

Remember: All the data you need is provided above. Analyze it directly and reference specific values.
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

            # Sheet selection to manage context size
            if len(st.session_state.data_summary) > 0:
                st.info("💡 Select sheets to analyze (reduces context size)")

                # Initialize selected sheets if not exists
                if "selected_sheets" not in st.session_state:
                    # Default: select key analysis sheets
                    key_sheets = ['GL Detail', '1. Income Statement', '2. Balance Sheet',
                                  '3. Cash Flow Statement', 'POC Lookback Summary']
                    default_selection = [s for s in key_sheets if s in st.session_state.data_summary.keys()]
                    if not default_selection:  # If key sheets not found, select first 5
                        default_selection = list(st.session_state.data_summary.keys())[:5]
                    st.session_state.selected_sheets = default_selection

                selected_sheets = st.multiselect(
                    "Sheets to include in analysis:",
                    options=list(st.session_state.data_summary.keys()),
                    default=st.session_state.selected_sheets,
                    help="Select fewer sheets if you hit context length errors"
                )
                st.session_state.selected_sheets = selected_sheets

                st.caption(f"Selected: {len(selected_sheets)} of {len(st.session_state.data_summary)} sheets")

                with st.expander("View all loaded sheets"):
                    for sheet_name in st.session_state.data_summary.keys():
                        selected_mark = "✓" if sheet_name in selected_sheets else "○"
                        st.write(f"{selected_mark} {sheet_name}")
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

                # Build messages for API - use selected sheets only
                selected_sheets = st.session_state.get("selected_sheets", list(st.session_state.data_summary.keys()))
                data_context = create_data_context(st.session_state.data_summary, selected_sheets)
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

            # Build messages for API - use selected sheets only
            selected_sheets = st.session_state.get("selected_sheets", list(st.session_state.data_summary.keys()))
            data_context = create_data_context(st.session_state.data_summary, selected_sheets)
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
