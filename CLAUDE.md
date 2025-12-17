# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a financial due diligence and analysis repository focused on company analysis through general ledger (GL) transaction data. The workflow progresses from raw transaction data to comprehensive analysis to management questions and action items.

## Analysis Workflow

1. **Source Data** → Transaction-level GL data serves as the foundation
2. **Databook Analysis** → Multiple analysis tabs built from GL transactions
3. **Management Questions** → Questions generated based on databook insights
4. **Response Tracking** → Management responses captured and converted to action items

## Repository Contents

- **Balance_Sheet_GL_Transactions (1).xlsx** - Working file containing source transaction data (7.6 MB)
  - Primary reference: "GL Detail" tab (shaded green)
  - Contains transaction-level data used to build all databook analysis tabs
  - Used for granular analysis and generating insights

- **Example Databook Output.xlsx** - Comprehensive company analysis workbook (516 KB)
  - Contains multiple analysis tabs built from GL transaction data
  - Reference template for the type and depth of analysis expected
  - Used to analyze companies in detail and generate meaningful questions

- **Task List.docx** - Management question tracking document
  - **Black font**: Questions for company management team
  - **Red font**: Company responses to questions
  - **Green font**: To-do items/action items based on management responses
  - Represents the expected format for question generation and response tracking

## Working with Files

Since this repository contains binary Office files, direct text-based tools cannot read them. When working with these files:

1. For Excel files (.xlsx), users will need to provide specific information about the data structure, columns, or requirements
2. For the Word document (.docx), users should share relevant content from the task list when needed
3. Any code development related to this repository would likely involve:
   - Python scripts using `pandas`, `openpyxl`, or `xlrd` for Excel manipulation
   - Data transformation or analysis scripts
   - Report generation automation

## Key Use Cases

The LLM should be capable of supporting the following workflows:

### 1. Data Analysis & Insights
- Read and interpret the "GL Detail" tab from Balance_Sheet_GL_Transactions (1).xlsx
- Generate insights and analysis from transaction-level data
- Identify patterns, anomalies, or areas requiring deeper investigation
- Create analytical views similar to the tabs in Example Databook Output.xlsx

### 2. Question Generation
- Analyze the databook to generate relevant questions for management
- Follow the format demonstrated in Task List.docx (questions in black font)
- Questions should be data-driven and based on insights from the analysis
- Focus on clarifying unusual transactions, trends, or business practices

### 3. Response Interpretation & Action Items
- Process management responses to questions
- Convert responses into actionable to-do items
- Follow the Task List format: responses (red) → action items (green)
- Prioritize follow-up analysis or data requests based on responses

## Development Setup

When developing scripts for this repository:

### Recommended Tools
- Python with `pandas` for data manipulation and analysis
- `openpyxl` or `xlsxwriter` for Excel file operations
- `python-docx` for Word document parsing and generation

### File References
- Source data: Always reference the "GL Detail" tab in Balance_Sheet_GL_Transactions (1).xlsx
- Analysis template: Use Example Databook Output.xlsx as the reference for analysis structure
- Question format: Follow the three-color system from Task List.docx

### Expected Capabilities
Scripts developed should be able to:
1. Parse GL transaction data and perform financial analysis
2. Generate databook-style analysis outputs with multiple tabs/views
3. Create management question lists based on data insights
4. Process Q&A sessions and generate action items
