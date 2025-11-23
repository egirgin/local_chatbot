# --- Global Application Configuration ---

import os

# --- PDF Functionality Check ---
# This must be at the top
PDF_FUNCTIONALITY_DISABLED = False
try:
    import pypdf
except ImportError:
    print("-------------------------------------------------")
    print("ERROR: 'pypdf' library not found.")
    print("Please install it: pip install pypdf")
    print("PDF functionality will be disabled.")
    print("-------------------------------------------------")
    PDF_FUNCTIONALITY_DISABLED = True
    pass

# --- Model Configuration ---
VLM_MODELS = [
    'moondream:v2',
    'moondream:latest',
    'llava:latest'
]
LLM_MODELS = [
    'gemma3:4b',
    'gemma3:1b',
    'qwen3:latest',
    'gemma:latest',
    'phi3:latest',
    'mistral:7b',
    'llama3.2:3b',
    'deepseek-r1:14b',
    'llama3:8b',
    'llama3.1:latest'
]

# Formatted list for dropdown
VLM_PREFIX = "[VLM] "
LLM_PREFIX = "[LLM] "
FORMATTED_VLM_MODELS = [f"{VLM_PREFIX}{model}" for model in VLM_MODELS]
FORMATTED_LLM_MODELS = [f"{LLM_PREFIX}{model}" for model in LLM_MODELS]
ALL_MODELS = FORMATTED_VLM_MODELS + FORMATTED_LLM_MODELS

# --- UI & Chat Configuration ---
THUMBNAIL_SIZE = (150, 150) # Size for attachment viewer
DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant. Be concise."

# --- File Extension Categories ---
PDF_EXTENSIONS = ['.pdf']
TEXT_EXTENSIONS = [
    '.py', '.m', '.cpp', '.c', '.h', '.java', '.js', '.ts',
    '.html', '.css', '.json', '.xml', '.yaml', '.yml', '.md',
    '.txt', '.kml', '.log'
]
IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.bmp', '.gif']


# --- Ollama & Retry Logic ---
MAX_RETRIES = 5
FORBIDDEN_KEYWORDS = [
    "as an ai",
    "as a large language model",
    "i cannot",
    "i am unable",
    "i'm not programmed to",
    "my purpose is to",
    "i do not have the ability",
    "i am an artificial intelligence",
    "I cannot",
    "I can't engage",
    "engage",
    "I am not able",
    "I can't help",
    "I can't fulfill",
    "help with that request",
    "I can't continue",
    "provide a response"
]