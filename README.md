# Financial Analysis Assistant

A Streamlit-based chat interface for analyzing financial GL transaction data using OpenAI's GPT-4o.

## Features

- **Two Analysis Modes:**
  - Use existing repository files
  - Upload your own Excel files

- **Interactive Chat Interface:**
  - Ask questions about financial data
  - Get insights and analysis
  - Request specific breakdowns

- **Deep Research Analysis:**
  - Automated comprehensive analysis
  - Pattern and anomaly detection
  - Management question generation

## Local Setup

### Prerequisites
- Python 3.8+
- OpenAI API key

### Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd MnARound2
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your OpenAI API key:
```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

4. Run the app:
```bash
streamlit run streamlit_app.py
```

The app will open in your browser at `http://localhost:8501`

## Usage

### Using Existing Files
1. Select "Use Existing Files" in the sidebar
2. Click "Load Repository Files"
3. Start chatting or run deep research analysis

### Uploading New Files
1. Select "Upload New Files" in the sidebar
2. Upload your Task List (optional) and Excel files
3. Click "Process Uploaded Files"
4. Start chatting or run deep research analysis

### Deep Research Analysis
Click the "🔍 Run Deep Research Analysis" button to get:
- Comprehensive data overview
- Key insights and trends
- Anomalies and red flags
- Suggested management questions

## Deploying to Streamlit Cloud

### Step 1: Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin <your-github-repo-url>
git push -u origin main
```

**Note:** The `.gitignore` file excludes `.env` and data files by default. If you want to include the Excel/Word files in your repo, comment out these lines in `.gitignore`:
```
# *.xlsx
# *.docx
```

### Step 2: Deploy on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with GitHub
3. Click "New app"
4. Select your repository and branch
5. Set main file path: `streamlit_app.py`
6. Click "Advanced settings"
7. Add your secrets:
   ```toml
   OPENAI_API_KEY = "your-api-key-here"
   ```
8. Click "Deploy"

Your app will be live at `https://your-app-name.streamlit.app`

## Project Structure

```
.
├── streamlit_app.py              # Main application
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment template
├── .gitignore                    # Git ignore rules
├── README.md                     # This file
├── CLAUDE.md                     # Development guide
├── Balance_Sheet_GL_Transactions (1).xlsx  # GL data
├── Example Databook Output.xlsx  # Analysis template
└── Task List.docx               # Q&A examples
```

## How It Works

1. **Data Loading:** The app reads Excel files and extracts key information (columns, sample data, statistics)

2. **Task List Examples:** Parses the Task List document to extract example questions/responses for context

3. **Chat Interface:** Sends your questions along with data context to GPT-4o for analysis

4. **Deep Research:** Runs a comprehensive analysis prompt that generates insights and management questions

## Limitations

- This is a POC focused on functionality over production-quality code
- Large Excel files may take time to process
- Data context is limited by GPT-4o's token limits (~128k tokens)
- Very large files may need to be analyzed in sections

## Troubleshooting

**"OpenAI API key not found"**
- Make sure your `.env` file exists and contains `OPENAI_API_KEY=your-key`
- For Streamlit Cloud, check that secrets are configured correctly

**"Error loading Excel file"**
- Ensure files are valid .xlsx format
- Check that files aren't corrupted
- Try re-saving the file in Excel

**Chat is slow**
- GPT-4o responses can take 10-30 seconds for complex analyses
- Large datasets require more processing time

## Future Enhancements

If this POC proves valuable, consider:
- Database integration for larger datasets
- RAG (Retrieval Augmented Generation) for huge files
- Export analysis results to reports
- Batch processing multiple files
- Custom analysis templates
