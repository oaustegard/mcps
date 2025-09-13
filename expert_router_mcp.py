from fastmcp import FastMCP
from pathlib import Path
import json
import yaml
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional

mcp = FastMCP("ICL Experts")

def calculate_experts_hash(experts: Dict[str, Any]) -> str:
    """Calculate hash of all expert data for versioning."""
    experts_str = json.dumps(experts, sort_keys=True)
    return hashlib.md5(experts_str.encode()).hexdigest()[:8]

def load_experts() -> Dict[str, Any]:
    """Load experts from files in ./experts/ directory."""
    experts = {}
    experts_dir = Path("experts")
    
    if not experts_dir.exists():
        experts_dir.mkdir()
        # Create example expert
        example_expert = {
            "name": "Python Development",
            "description": "Python development, debugging, architecture, testing",
            "system_prompt": "You are a Python development expert focusing on clean, maintainable code.",
            "core_patterns": [
                "Use dataclasses for structured data",
                "Prefer pathlib over os.path",
                "Write tests first for complex logic",
                "Handle exceptions specifically"
            ],
            "process_steps": [
                "Understand the data flow and error points",
                "Choose appropriate architectural patterns", 
                "Implement with proper error handling",
                "Validate through systematic testing"
            ],
            "keywords": ["python", "code", "debug", "test", "class", "function"]
        }
        
        with open(experts_dir / "python_dev.json", "w") as f:
            json.dump(example_expert, f, indent=2)
    
    # Load all expert files
    for file_path in experts_dir.glob("*.json"):
        expert_id = file_path.stem
        try:
            with open(file_path) as f:
                experts[expert_id] = json.load(f)
        except Exception as e:
            print(f"Error loading expert {expert_id}: {e}")
    
    for file_path in experts_dir.glob("*.yaml"):
        expert_id = file_path.stem
        try:
            with open(file_path) as f:
                experts[expert_id] = yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading expert {expert_id}: {e}")
    
    return experts

@mcp.tool
def get_project_instruction(current_version: Optional[str] = None) -> str:
    """
    Get the complete Claude project instruction with expert list and version.
    Compares against current_version to detect if update is needed.
    """
    experts = load_experts()
    version = calculate_experts_hash(experts)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    
    # Check if update needed
    update_notice = ""
    if current_version and current_version != version:
        update_notice = f"""
🔄 **UPDATE REQUIRED**
Your project instruction version ({current_version}) is outdated.
Current version: {version}
Please replace your Claude project instruction with the content below.

---
"""
    elif current_version == version:
        update_notice = "✅ Your project instruction is up to date.\n\n---\n"
    
    # Generate expert list
    expert_list = ""
    for expert_id, expert in experts.items():
        expert_list += f"- **{expert_id}**: {expert.get('description', 'No description')}\n"
    
    # Complete project instruction
    instruction = f"""{update_notice}
# Expert-Enhanced Assistant

**Version:** {version} (Generated: {timestamp})

You are an AI assistant with access to specialized expert knowledge through the ICL Experts MCP server.

## Available Experts

{expert_list}

## Process for Complex Queries

When handling technical or specialized questions:

1. **Identify the domain** - Determine which expert(s) would be most relevant
2. **Consult expert knowledge** using `consult_expert(expert_id)` for single domain questions
3. **Use multiple experts** with `consult_multiple_experts([expert_ids])` for cross-domain questions  
4. **Apply expert frameworks** - Use the returned system prompts, patterns, and processes
5. **Synthesize response** - Combine expert knowledge with your reasoning

## Decision Guidelines

- **Single expert**: Questions clearly in one domain (e.g., "How to optimize Python code?" → `python_dev`)
- **Multiple experts**: Complex questions spanning domains (e.g., "Build a scalable data pipeline" → `["python_dev", "data_analysis", "system_design"]`)
- **No expert needed**: Simple questions you can answer directly

## Usage Examples

```python
# Single expert consultation
expert_knowledge = consult_expert("python_dev")
# Apply the returned patterns and processes to your response

# Multiple expert consultation  
multi_expert_knowledge = consult_multiple_experts(["data_analysis", "system_design"])
# Synthesize insights from multiple expert perspectives
```

Always explain which expert knowledge you're applying when you consult experts, so users understand the specialized frameworks being used.

---

**Instructions for updating:**
1. Copy this entire instruction 
2. Replace your current Claude project system prompt
3. Keep this version number: `{version}` for future update checks"""
    
    return instruction

@mcp.tool
def consult_expert(expert_id: str) -> str:
    """Get complete knowledge from a specific expert."""
    experts = load_experts()
    
    if expert_id not in experts:
        available = list(experts.keys())
        return json.dumps({
            "error": f"Expert '{expert_id}' not found",
            "available": available
        })
    
    expert = experts[expert_id]
    return json.dumps({
        "expert_id": expert_id,
        "name": expert.get("name", expert_id),
        "system_prompt": expert.get("system_prompt", ""),
        "core_patterns": expert.get("core_patterns", []),
        "process_steps": expert.get("process_steps", [])
    }, indent=2)

@mcp.tool
def consult_multiple_experts(expert_ids: list[str]) -> str:
    """Get knowledge from multiple experts."""
    experts = load_experts()
    results = {}
    
    for expert_id in expert_ids:
        if expert_id in experts:
            expert = experts[expert_id]
            results[expert_id] = {
                "name": expert.get("name", expert_id),
                "system_prompt": expert.get("system_prompt", ""),
                "core_patterns": expert.get("core_patterns", []),
                "process_steps": expert.get("process_steps", [])
            }
        else:
            results[expert_id] = {"error": f"Expert '{expert_id}' not found"}
    
    return json.dumps(results, indent=2)

@mcp.tool
def get_current_version() -> str:
    """Get current expert system version."""
    experts = load_experts()
    version = calculate_experts_hash(experts)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    
    return json.dumps({
        "version": version,
        "timestamp": timestamp,
        "expert_count": len(experts),
        "experts": list(experts.keys())
    }, indent=2)

@mcp.tool
def list_expert_files() -> str:
    """List all expert files found in ./experts/ directory."""
    experts_dir = Path("experts")
    
    if not experts_dir.exists():
        return "No experts directory found. Will be created on first expert load."
    
    files = []
    for pattern in ["*.json", "*.yaml"]:
        files.extend(experts_dir.glob(pattern))
    
    if not files:
        return "No expert files found in ./experts/ directory"
    
    file_info = "Expert files found:\n"
    for file_path in sorted(files):
        stat = file_path.stat()
        modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
        file_info += f"- {file_path.name} (modified: {modified})\n"
    
    return file_info
