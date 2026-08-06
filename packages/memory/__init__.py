"""
Engineering Memory package for capturing architectural choices, conventions, and project history.
"""
from pathlib import Path

def generate_overview(memory_entries: list[dict]) -> str:
    """Synthesize project memory notes into a coherent engineering decision log."""
    if not memory_entries:
        return "No engineering memory notes recorded for this repository yet."
    
    lines = ["## Project Engineering Memory Log\n"]
    for idx, entry in enumerate(memory_entries, 1):
        lines.append(f"{idx}. **[{entry.get('category', 'General')}]** {entry.get('title', 'Note')}: {entry.get('content', '')}")
    return "\n".join(lines)
