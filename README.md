# LLM-Powered File System Assistant

An intelligent file system assistant that uses LLMs (Large Language Models) with tool-calling capabilities to read, search, list, and write files. The project demonstrates clean architecture with pluggable LLM providers (OpenAI, Gemini) following SOLID principles.

## ✨ Features

- 🤖 **Multi-LLM Support**: Switch between OpenAI and Google Gemini seamlessly
- 🔧 **Tool Calling**: Automatic function execution with multi-step reasoning
- 📁 **Smart File Search**: Automatically searches in `data/` and `resumes/` folders
- 📄 **Multiple Formats**: Supports PDF, DOCX, TXT files
- 🔍 **Search & Filter**: Search keywords in files, list files by extension
- 📝 **Write Files**: Create and write content to files
- 🎯 **Verbose Logging**: See every tool call and LLM step in action
- 🏗️ **Extensible Design**: Easy to add new LLM providers without code changes

## 📋 Prerequisites

- Python 3.9+
- OpenAI API Key (for OpenAI provider) OR Google Gemini API Key (for Gemini provider)

## 🚀 Quick Start

### 1. Clone and Setup

```bash
cd LLM-Powered-File-System-Assistant
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the project root:

```env
# Choose your LLM provider (default: openai)
LLM_PROVIDER=openai

# OpenAI Configuration
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_MODEL=gpt-4-turbo

# OR Gemini Configuration
# LLM_PROVIDER=gemini
# GEMINI_API_KEY=your-gemini-api-key-here
# GEMINI_MODEL=gemini-2.0-flash
```

### 3. Install Dependencies

```bash
pip install openai google-genai python-dotenv PyPDF2 python-docx
```

Or use the requirements file:
```bash
pip install -r requirements.txt
```

### 4. Run the Assistant

```bash
python llm_file_assistant.py
```

## 💡 Usage Examples

### Example 1: Read and Summarize a PDF
```
Enter your query: Read adaptive-cv.pdf and summarize the key skills
```

### Example 2: Search in Multiple Files
```
Enter your query: Search for "Python" in all files in the data folder
```

### Example 3: List Files
```
Enter your query: List all PDF files in the resumes directory
```

### Example 4: Search Keywords
```
Enter your query: Find all occurrences of "machine learning" in report.txt
```

### Example 5: Multi-step Operations
```
Enter your query: Read all resumes from the data folder, compare them, and write a summary to output.txt
```

## 📁 Project Structure

```
LLM-Powered-File-System-Assistant/
├── llm_file_assistant.py   # Main entry point with LLM provider implementation
├── fs_tools.py              # File system tools (read, write, search, list)
├── README.md                # Project documentation
├── .env                     # Environment configuration (create this)
├── requirements.txt         # Python dependencies
├── data/                    # Default folder for file operations
└── resumes/                 # Example folder for resume files
```

## 🔧 Configuration Options

### Environment Variables

| Variable | Options | Default | Description |
|----------|---------|---------|-------------|
| `LLM_PROVIDER` | `openai`, `gemini` | `openai` | Choose LLM provider |
| `OPENAI_API_KEY` | Your API key | - | OpenAI API key (required for OpenAI) |
| `OPENAI_MODEL` | Model name | `gpt-4.1` | OpenAI model to use |
| `GEMINI_API_KEY` | Your API key | - | Google Gemini API key (required for Gemini) |
| `GEMINI_MODEL` | Model name | `gemini-3-flash-preview` | Gemini model to use |

### Switching Providers

**Option 1: Environment Variable**
```bash
# Windows PowerShell
$env:LLM_PROVIDER="gemini"
python llm_file_assistant.py

# Linux/Mac
export LLM_PROVIDER=gemini
python llm_file_assistant.py
```

**Option 2: .env File**
```env
LLM_PROVIDER=gemini
```

**Option 3: In Code**
```python
from llm_file_assistant import ask_llm

# Force use OpenAI for this query
result = ask_llm("Read data.txt", provider="openai")

# Force use Gemini for this query
result = ask_llm("Analyze report.pdf", provider="gemini")
```

## 🛠️ Available Tools

The assistant has access to the following tools:

| Tool | Parameters | Description |
|------|------------|-------------|
| `read_file` | `filepath: str` | Read PDF, TXT, DOCX files and extract content |
| `list_files` | `directory: str`, `extension?: str` | List files in a directory with optional filter |
| `search_in_file` | `filepath: str`, `keyword: str` | Search for keywords in files with context |
| `write_file` | `filepath: str`, `content: str` | Write content to a file (creates dirs if needed) |

## 🎬 Demo Scenarios (for Video)

### Scenario 1: OpenAI with File Reading
```python
python llm_file_assistant.py
# Query: Read adaptive-cv.pdf and extract the candidate's top 5 skills
```

### Scenario 2: Switch to Gemini
```python
# Update .env: LLM_PROVIDER=gemini
python llm_file_assistant.py
# Query: List all files in data folder and tell me which ones are PDFs
```

### Scenario 3: Multi-Step Reasoning
```python
# Query: Read all resumes in data/, compare their experience levels, and write a ranking to rankings.txt
```

## 🏗️ Architecture

### Design Principles

- **Single Responsibility**: Each class has one clear purpose
- **Open/Closed**: Easy to extend with new providers without modifying existing code
- **Liskov Substitution**: All providers implement the same interface
- **Dependency Inversion**: High-level code depends on abstractions, not concrete implementations
- **Simple & Readable**: No over-engineering, clean separation of concerns

### Adding a New LLM Provider

1. Create a new class inheriting from `LLMProvider`:

```python
class NewProvider(LLMProvider):
    def __init__(self, model: Optional[str] = None):
        # Initialize your LLM client
        pass
    
    def create_message(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Call your LLM API
        pass
    
    def extract_tool_calls(self, assistant_message: Dict[str, Any]) -> List[ToolCall]:
        # Parse tool calls from response
        pass
    
    def get_text(self, assistant_message: Dict[str, Any]) -> str:
        # Extract text response
        pass
```

2. Register in `_get_provider()`:

```python
def _get_provider(provider: Optional[str] = None) -> LLMProvider:
    name = (provider or os.getenv("LLM_PROVIDER", "openai")).strip().lower()
    
    if name in {"openai", "oai"}:
        return OpenAIProvider()
    if name in {"gemini", "google"}:
        return GeminiProvider()
    if name == "newprovider":
        return NewProvider()
    
    raise ValueError(f"Unknown LLM_PROVIDER '{name}'")
```

## 📊 Verbose Output Example

When you run a query, you'll see detailed logging:

```
============================================================
🚀 LLM Provider: OPENAI
📝 Query: Read data.txt and summarize it
============================================================

[Step 1] Calling LLM...
  💭 Assistant: I'll read the file first...

  → LLM wants to use 1 tool(s)...

  🔧 [TOOL CALL] read_file
     Args: {
            "filepath": "data.txt"
          }
     ✓ Result: The file contains information about...

[Step 2] Calling LLM...
  💭 Assistant: Based on the file contents...

✅ Final Answer (No tools needed):
────────────────────────────────────────────────────────────
Here's a summary of data.txt:
- Key point 1
- Key point 2
- Key point 3
────────────────────────────────────────────────────────────
```

## 🐛 Troubleshooting

### Issue: "File not found"
- Files are automatically searched in `data/`, `resumes/`, and current directory
- Provide full path: `data/myfile.pdf` or just `myfile.pdf`

### Issue: "Quota exceeded" (Gemini)
- Switch to OpenAI: `LLM_PROVIDER=openai`
- Wait for quota reset (check Google AI Studio)

### Issue: "Invalid API key"
- Check `.env` file exists and contains correct keys
- Ensure `python-dotenv` is installed
- Verify key format (no quotes in .env)

### Issue: Tool calls not working
- Check LLM model supports function calling
- OpenAI: Use `gpt-4-turbo`, `gpt-4o`, or `gpt-3.5-turbo`
- Gemini: Uses JSON-based tool calling (works with all models)

## 📝 Requirements

```txt
openai>=1.0.0
google-genai>=0.2.0
python-dotenv>=1.0.0
PyPDF2>=3.0.0
python-docx>=1.0.0
```

## 🤝 Contributing

To add new file formats or tools:

1. Add tool function to `fs_tools.py`
2. Register in `FUNCTION_MAP` in `llm_file_assistant.py`
3. Add tool schema to `TOOLS` list

## 📄 License

MIT License - feel free to use this for your projects!

## 🎓 Learning Outcomes

This project demonstrates:
- LLM tool/function calling
- Provider pattern for extensibility
- Clean architecture principles
- Multi-step AI reasoning
- Environment-based configuration
- Error handling and logging