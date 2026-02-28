import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from fs_tools import list_files, read_file, search_in_file, write_file
from dotenv import load_dotenv
load_dotenv()

TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file and extract its text content. Supports .txt, .pdf, .json, .md, and other text-based formats. For PDFs, extracts text from all pages.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Path to the file (e.g., 'report.pdf', 'data/cv.pdf')"}
                },
                "required": ["filepath"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in a directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {"type": "string"},
                    "extension": {"type": "string"}
                },
                "required": ["directory"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_in_file",
            "description": "Search keyword in a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string"},
                    "keyword": {"type": "string"}
                },
                "required": ["filepath", "keyword"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to file",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["filepath", "content"]
            }
        }
    },
]

FUNCTION_MAP = {
    "read_file": read_file,
    "list_files": list_files,
    "write_file": write_file,
    "search_in_file": search_in_file,
}


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: Dict[str, Any]
    tool_call_id: Optional[str] = None


class LLMProvider:
    """Small abstraction for pluggable LLM providers."""

    def create_message(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        raise NotImplementedError

    def extract_tool_calls(self, assistant_message: Dict[str, Any]) -> List[ToolCall]:
        raise NotImplementedError

    def get_text(self, assistant_message: Dict[str, Any]) -> str:
        raise NotImplementedError


class OpenAIProvider(LLMProvider):
    def __init__(self, model: Optional[str] = None):
        from openai import OpenAI

        self._client = OpenAI()
        self._model = model or os.getenv("OPENAI_MODEL", "gpt-4.1")

    def create_message(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )
        msg = response.choices[0].message

        tool_calls: Optional[List[Dict[str, Any]]] = None
        if msg.tool_calls:
            tool_calls = []
            for tc in msg.tool_calls:
                tool_calls.append(
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                )

        # API-compatible assistant message (important for tool-call continuation).
        return {"role": "assistant", "content": msg.content, "tool_calls": tool_calls}

    def extract_tool_calls(self, assistant_message: Dict[str, Any]) -> List[ToolCall]:
        tool_calls = assistant_message.get("tool_calls") or []
        results: List[ToolCall] = []

        for tc in tool_calls:
            if not isinstance(tc, dict):
                continue
            func = tc.get("function") or {}
            func_name = func.get("name")
            raw_args = func.get("arguments")

            if not isinstance(func_name, str):
                continue
            try:
                args = json.loads(raw_args or "{}") if isinstance(raw_args, str) else {}
            except json.JSONDecodeError:
                args = {}

            results.append(ToolCall(name=func_name, arguments=args, tool_call_id=tc.get("id")))

        return results

    def get_text(self, assistant_message: Dict[str, Any]) -> str:
        return assistant_message.get("content") or ""


class GeminiProvider(LLMProvider):
    """Gemini provider using the `google-genai` SDK.

    To keep this project simple and extendable, we use a lightweight
    tool-calling convention (JSON) instead of SDK-specific function calling.
    """

    def _tool_prompt(self) -> str:
        tool_lines: List[str] = []
        for t in TOOLS:
            f = (t.get("function") or {})
            name = f.get("name")
            params = (f.get("parameters") or {}).get("properties") or {}
            if not isinstance(name, str):
                continue
            param_names = ", ".join(sorted(params.keys()))
            tool_lines.append(f"- {name}({param_names})")

        tools_summary = "\n".join(tool_lines) if tool_lines else "(no tools)"

        return (
            "You are a file-system assistant. You can call tools to read/list/search/write files.\n"
            "Available tools:\n"
            f"{tools_summary}\n\n"
            "If you need to call a tool, respond with ONLY valid JSON in this exact shape:\n"
            "{\"tool_calls\":[{\"name\":\"tool_name\",\"arguments\":{...}}]}\n"
            "You may include multiple tool calls in the list.\n"
            "If you do not need tools, respond with the final answer as plain text (no JSON)."
        )

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None):
        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("Missing GEMINI_API_KEY environment variable")

        # Import lazily so OpenAI-only usage doesn't require this dependency.
        from google import genai as google_genai

        self._client = google_genai.Client(api_key=api_key)
        self._model = model or os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")

    def _format_prompt(self, messages: List[Dict[str, Any]]) -> str:
        parts: List[str] = [self._tool_prompt(), "\nConversation:"]

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content") or ""
            name = msg.get("name")

            if role == "user":
                parts.append(f"User: {content}")
            elif role == "assistant":
                parts.append(f"Assistant: {content}")
            elif role == "tool":
                tool_name = name or "tool"
                parts.append(f"Tool[{tool_name}] result: {content}")
            else:
                parts.append(f"{role}: {content}")

        parts.append("Assistant:")
        return "\n".join(parts)

    def create_message(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        prompt = self._format_prompt(messages)
        response = self._client.models.generate_content(model=self._model, contents=prompt)
        text = getattr(response, "text", None) or ""
        return {"role": "assistant", "content": text, "tool_calls": None}

    def extract_tool_calls(self, assistant_message: Dict[str, Any]) -> List[ToolCall]:
        text = (assistant_message.get("content") or "").strip()
        if not text:
            return []

        # Allow markdown fenced JSON.
        if text.startswith("```"):
            lines = text.splitlines()
            if len(lines) >= 3 and lines[0].startswith("```") and lines[-1].startswith("```"):
                text = "\n".join(lines[1:-1]).strip()

        if not (text.startswith("{") and text.endswith("}")):
            return []

        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return []

        raw_calls = payload.get("tool_calls")
        if not isinstance(raw_calls, list):
            return []

        calls: List[ToolCall] = []
        for raw_call in raw_calls:
            if not isinstance(raw_call, dict):
                continue
            name = raw_call.get("name")
            arguments = raw_call.get("arguments") or {}
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {}
            if isinstance(name, str) and isinstance(arguments, dict):
                calls.append(ToolCall(name=name, arguments=arguments))

        return calls

    def get_text(self, assistant_message: Dict[str, Any]) -> str:
        return assistant_message.get("content") or ""


def _get_provider(provider: Optional[str] = None) -> LLMProvider:
    name = (provider or os.getenv("LLM_PROVIDER", "openai")).strip().lower()

    if name in {"openai", "oai"}:
        return OpenAIProvider()
    if name in {"gemini", "google"}:
        return GeminiProvider()

    raise ValueError(
        f"Unknown LLM_PROVIDER '{name}'. Supported: 'openai', 'gemini'."
    )


def _execute_tool_call(call: ToolCall) -> Dict[str, Any]:
    """Execute a single tool call and print progress."""
    func = FUNCTION_MAP.get(call.name)
    if not func:
        return {"success": False, "error": f"Unknown tool: {call.name}"}

    # Print tool call details for demo visibility
    print(f"\n  🔧 [TOOL CALL] {call.name}")
    print(f"     Args: {json.dumps(call.arguments, indent=6)}")
    
    try:
        result = func(**call.arguments)
        
        # Print result preview
        if isinstance(result, dict):
            if result.get("success"):
                content = result.get("content", "")
                preview = (content[:100] + "...") if len(str(content)) > 100 else content
                print(f"     ✓ Result: {preview}")
            else:
                print(f"     ✗ Error: {result.get('error')}")
        else:
            print(f"     ✓ Result: {json.dumps(result, indent=6)[:100]}")
        
        return result
    except TypeError as e:
        error_msg = f"Invalid arguments for {call.name}: {e}"
        print(f"     ✗ Error: {error_msg}")
        return {"success": False, "error": error_msg}
    except Exception as e:
        error_msg = str(e)
        print(f"     ✗ Error: {error_msg}")
        return {"success": False, "error": error_msg}


def ask_llm(query: str, provider: Optional[str] = None, max_steps: int = 8) -> str:
    """Ask the configured LLM to solve a user query.

    - Select provider via `provider=` or env var `LLM_PROVIDER` ('openai' | 'gemini')
    - Supports multi-step tool calling until a final answer is produced.
    - Logs all tool calls and results to terminal for visibility.
    """

    llm = _get_provider(provider)
    provider_name = provider or os.getenv("LLM_PROVIDER", "openai")
    
    print(f"\n{'='*60}")
    print(f"🚀 LLM Provider: {provider_name.upper()}")
    print(f"📝 Query: {query}")
    print(f"{'='*60}")
    
    messages: List[Dict[str, Any]] = [{"role": "user", "content": query}]
    step = 0

    for step in range(max_steps):
        step += 1
        print(f"\n[Step {step}] Calling LLM...")
        
        assistant_message = llm.create_message(messages)
        assistant_text = llm.get_text(assistant_message)
        messages.append(assistant_message)
        
        # Show assistant's thinking/response
        response_preview = (assistant_text[:150] + "...") if len(assistant_text) > 150 else assistant_text
        print(f"  💭 Assistant: {response_preview}")

        # Check if assistant wants to use tools
        tool_calls = llm.extract_tool_calls(assistant_message)
        if not tool_calls:
            print(f"\n✅ Final Answer (No tools needed):")
            print(f"{'-'*60}")
            print(assistant_text)
            print(f"{'-'*60}")
            return assistant_text.strip()

        # Execute all tool calls
        print(f"\n  → LLM wants to use {len(tool_calls)} tool(s)...")
        for i, call in enumerate(tool_calls, 1):
            tool_result = _execute_tool_call(call)
            tool_msg: Dict[str, Any] = {
                "role": "tool",
                "name": call.name,
                "content": json.dumps(tool_result, ensure_ascii=False),
            }
            if call.tool_call_id:
                tool_msg["tool_call_id"] = call.tool_call_id
            messages.append(tool_msg)

    return "❌ I couldn't complete the request within the tool-calling step limit."


if __name__ == "__main__":
    query = input("Enter your query for the file assistant: ")
    ask_llm(query)