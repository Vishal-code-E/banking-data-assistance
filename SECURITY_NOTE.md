# Running Tests Securely

## Setup API Key

**IMPORTANT:** Never commit your OpenAI API key to git!

### Option 1: Environment Variable (Recommended)
```bash
export OPENAI_API_KEY="your-api-key-here"
python3 ai_engine/main.py
```

### Option 2: .env File
1. Create a `.env` file in the project root:
```bash
cp .env.example .env
```

2. Edit `.env` and add your API key:
```
OPENAI_API_KEY=your-actual-api-key-here
```

3. The `.env` file is already in `.gitignore` and won't be committed

## Running the AI Assistant

```bash
# Set your API key first
export OPENAI_API_KEY="sk-proj-your-key-here"

# Run the main demo
python3 ai_engine/main.py

# Or create your own test script
python3 -c "
import os
os.environ['OPENAI_API_KEY'] = 'your-key'  # Only in local scripts!
from ai_engine.main import run_banking_assistant
result = run_banking_assistant('show customers who spent above 10000')
print(result)
"
```

## What I Fixed

✅ Removed hardcoded API key from test files  
✅ Added test files to `.gitignore`  
✅ Amended git commit to remove sensitive data  
✅ Successfully pushed to GitHub  

**Your API key is no longer exposed in the repository!**
