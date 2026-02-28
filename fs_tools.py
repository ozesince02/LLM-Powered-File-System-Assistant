import os
from datetime import datetime
from typing import List, Dict, Optional

from PyPDF2 import PdfReader
from docx import Document


def _find_file(filepath: str) -> Optional[str]:
    """Find file in current dir, data folder, or subdirectories.
    
    Search order:
    1. Direct path
    2. data/ folder
    3. resumes/ folder
    4. Any subdirectory
    """
    # If file exists as-is, use it
    if os.path.isfile(filepath):
        return filepath
    
    # Search in common data directories
    for search_dir in ["data", "resumes", "documents", "files"]:
        full_path = os.path.join(search_dir, filepath)
        if os.path.isfile(full_path):
            return full_path
    
    # If filename only (no path), search all subdirs in data
    basename = os.path.basename(filepath)
    for search_dir in ["data", "resumes"]:
        if os.path.isdir(search_dir):
            for root, _, files in os.walk(search_dir):
                for file in files:
                    if file == basename:
                        return os.path.join(root, file)
    
    return None


def read_file(filepath: str) -> Dict:
    """
    Read PDF, TXT, DOCX files and return structured response.
    Automatically searches data/ folder if file not found directly.
    """
    try:
        # Find file in data folder or subdirectories
        actual_path = _find_file(filepath)
        if not actual_path:
            return {"success": False, "error": f"File '{filepath}' not found. Searched: current dir, data/, resumes/"}

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
    List files in directory with optional extension filter.
    Automatically searches in data/ folder if directory not found.
    """
    # If directory not found directly, try in data/
    if not os.path.isdir(directory) and os.path.isdir(os.path.join("data", directory)):
        directory = os.path.join("data", directory)
    
    if not os.path.isdir(directory):
        return []

    results = []

    for file in os.listdir(directory):
        path = os.path.join(directory, file)

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
    Write content to file. Creates directories if needed.
    """
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return {"success": True, "path": filepath}

    except Exception as e:
        return {"success": False, "error": str(e)}


def search_in_file(filepath: str, keyword: str) -> Dict:
    """
    Search keyword in file and return matches with context.
    Automatically searches data/ folder if file not found.
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