import os
from datetime import datetime
from typing import List, Dict, Optional

from PyPDF2 import PdfReader
from docx import Document

DATA_DIR = "data"  # Only folder where LLM can operate


def _is_safe_path(filepath: str) -> bool:
    """Check if path is within the data/ folder (security check).
    
    Prevents LLM from accessing files outside data/ folder.
    """
    # Normalize path
    filepath = os.path.normpath(filepath)
    
    # If it's just a filename, it will be in data/ anyway
    if os.path.sep not in filepath:
        return True
    
    # Check if path tries to escape data folder (../)
    if ".." in filepath:
        return False
    
    # Check if path goes to root or other dirs
    if filepath.startswith(os.path.sep) or os.path.isabs(filepath):
        return False
    
    return True


def _get_data_path(filepath: str) -> Optional[str]:
    """Get full path in data/ folder. Returns None if unsafe.
    
    This is the ONLY function that constructs file paths.
    All tools must use this to enforce data-folder-only access.
    """
    if not _is_safe_path(filepath):
        return None
    
    # Always prepend data/ folder
    full_path = os.path.join(DATA_DIR, filepath)
    full_path = os.path.normpath(full_path)  # Normalize to prevent escape attempts
    
    # Final check: ensure normalized path is still in data/
    try:
        # Get absolute paths for comparison
        abs_data = os.path.abspath(DATA_DIR)
        abs_full = os.path.abspath(full_path)
        
        # Ensure full_path is under data/
        if not abs_full.startswith(abs_data):
            return None
    except:
        return None
    
    return full_path


def read_file(filepath: str) -> Dict:
    """
    Read PDF, TXT, DOCX files from data/ folder only.
    Returns error if file is outside data/ folder.
    """
    try:
        # Get safe path in data/ folder only
        actual_path = _get_data_path(filepath)
        if not actual_path or not os.path.isfile(actual_path):
            return {"success": False, "error": f"Access denied or file not found: '{filepath}'. Only files in data/ folder are allowed."}

        ext = os.path.splitext(actual_path)[1].lower()
        content = ""

        if ext == ".txt":
            with open(actual_path, "r", encoding="utf-8") as f:
                content = f.read()

        elif ext == ".pdf":
            reader = PdfReader(actual_path)
            content = "\n".join(page.extract_text() or "" for page in reader.pages)

        elif ext == ".docx":
            doc = Document(actual_path)
            content = "\n".join(p.text for p in doc.paragraphs)

        else:
            return {"success": False, "error": f"Unsupported file type: {ext}"}

        metadata = {
            "filename": os.path.basename(actual_path),
            "size_bytes": os.path.getsize(actual_path),
            "modified": datetime.fromtimestamp(
                os.path.getmtime(actual_path)
            ).isoformat(),
            "extension": ext,
        }

        return {"success": True, "content": content, "metadata": metadata}

    except Exception as e:
        return {"success": False, "error": str(e)}


def list_files(directory: str, extension: Optional[str] = None) -> List[Dict]:
    """
    List files in data/ folder with optional extension filter.
    Only allows operations within data/ folder.
    """
    # Get safe path in data/ folder
    safe_dir = _get_data_path(directory) if directory else os.path.join(DATA_DIR)
    
    if not safe_dir or not os.path.isdir(safe_dir):
        return []

    results = []

    for file in os.listdir(safe_dir):
        path = os.path.join(safe_dir, file)

        if not os.path.isfile(path):
            continue

        if extension and not file.lower().endswith(extension.lower()):
            continue

        results.append({
            "name": file,
            "size_bytes": os.path.getsize(path),
            "modified": datetime.fromtimestamp(
                os.path.getmtime(path)
            ).isoformat(),
            "path": path
        })

    return results


def write_file(filepath: str, content: str) -> Dict:
    """
    Write content to file in data/ folder only.
    Creates subdirectories if needed, but only within data/.
    """
    try:
        # Get safe path in data/ folder
        safe_path = _get_data_path(filepath)
        if not safe_path:
            return {"success": False, "error": "Access denied. Only files in data/ folder are allowed."}
        
        # Create parent directory if needed (but only in data/)
        parent_dir = os.path.dirname(safe_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        with open(safe_path, "w", encoding="utf-8") as f:
            f.write(content)

        return {"success": True, "path": safe_path}

    except Exception as e:
        return {"success": False, "error": str(e)}


def search_in_file(filepath: str, keyword: str) -> Dict:
    """
    Search keyword in file within data/ folder only.
    Returns error if file is outside data/ folder.
    """
    result = read_file(filepath)

    if not result.get("success"):
        return result

    text = result["content"]
    keyword_lower = keyword.lower()
    matches = []

    lines = text.splitlines()

    for i, line in enumerate(lines):
        if keyword_lower in line.lower():
            context = "\n".join(lines[max(0, i-1): i+2])
            matches.append(context)

    return {
        "success": True,
        "matches_found": len(matches),
        "matches": matches
    }