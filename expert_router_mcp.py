from fastmcp import FastMCP
from pathlib import Path
import hashlib
from datetime import datetime
from typing import Dict, Optional
import re

mcp = FastMCP(
    name="ICL Experts",
    instructions="""In-Context Learning (ICL) Experts providing specialized domain knowledge.

IMPORTANT: If a user asks about ICL Experts usage, setup, or configuration, 
ALWAYS call get_project_instruction() first (without version parameter) to provide current setup instructions, 
then explain usage (deep insights can be provided by the experts_README expert). This ensures new users get 
immediately actionable setup instructions.

For expert consultations, use consult_expert(expert_id) or consult_multiple_experts([ids]).
For expert discovery, use list_experts()."""
)

def extract_role(content: str) -> str:
    """
    Extract role definition from expert file using flexible patterns.
    
    Prioritizes rich role content over simple description labels.
    Supports any format with minimal syntax requirements.
    """
    
    # Try patterns in order of richness/preference
    patterns = [
        # Role tags (preferred - contains methodology and approach)
        (r'<role>\s*(.+?)\s*</role>', "role definition"),
        
        # System prompt as good fallback (often contains role info)
        (r'<system_prompt>\s*(.+?)\s*</system_prompt>', "system prompt"),
        (r'"system_prompt"\s*:\s*"([^"]+)"', "system prompt"),
        
        # Legacy description fields for backward compatibility
        (r'"description"\s*:\s*"([^"]+)"', "JSON description"),
        (r"'description'\s*:\s*'([^']+)'", "JSON description"),
        (r'^description\s*:\s*(.+?)(?=\n\w|\n#|\Z)', "YAML description"),
        (r'<description[^>]*>\s*(.+?)\s*</description>', "XML description"),
        
        # Markdown-style headers
        (r'^#\s*Role\s*\n(.+?)(?=\n#|\n\n|\Z)', "Markdown role"),
        (r'^##\s*Role\s*\n(.+?)(?=\n#|\n\n|\Z)', "Markdown role"),
        (r'^#\s*Description\s*\n(.+?)(?=\n#|\n\n|\Z)', "Markdown description"),
        
        # Comment-style
        (r'#\s*ROLE\s*:\s*(.+)$', "comment role"),
        (r'//\s*ROLE\s*:\s*(.+)$', "comment role"),
        (r'#\s*DESCRIPTION\s*:\s*(.+)$', "comment description"),
        (r'//\s*DESCRIPTION\s*:\s*(.+)$', "comment description"),
        
        # Simple line format
        (r'^Role\s*:\s*(.+)$', "line role"),
        (r'^Description\s*:\s*(.+)$', "line description"),
    ]
    
    for pattern, source_type in patterns:
        match = re.search(pattern, content, re.MULTILINE | re.IGNORECASE | re.DOTALL)
        if match:
            role = match.group(1).strip()
            # Clean up multi-line content for listing purposes
            if '\n' in role:
                # Take first substantial sentence or paragraph
                lines = [line.strip() for line in role.split('\n') if line.strip()]
                if lines:
                    first_line = lines[0]
                    # If first line is very short, try to include more context
                    if len(first_line) < 50 and len(lines) > 1:
                        role = f"{first_line} {lines[1]}"
                    else:
                        role = first_line
            
            # Truncate if too long for listing
            if len(role) > 250:
                role = role[:247] + "..."
                
            return role
    
    # Ultimate fallback
    return "This expert doesn't have a designated role - alert user and attempt to infer from expert id"

def load_experts() -> Dict[str, Dict[str, str]]:
    """
    Load all expert files as plain text.
    
    Supports ANY text-based format: .txt, .md, .json, .xml, .yaml, .yml, etc.
    Requires only that a role can be extracted for listing purposes.
    """
    experts = {}
    experts_dir = Path("experts")
    
    # Create directory if it doesn't exist, but don't populate it
    if not experts_dir.exists():
        experts_dir.mkdir()
        print("Created ./experts/ directory. Add your expert files here!")
    
    # Load ALL text files (any extension)
    text_extensions = {'.txt', '.md', '.json', '.xml', '.yaml', '.yml', '.py', '.js', '.html'}
    
    for file_path in experts_dir.iterdir():
        if file_path.is_file() and (file_path.suffix.lower() in text_extensions or not file_path.suffix):
            try:
                # Read entire file as text
                content = file_path.read_text(encoding='utf-8')
                
                # Extract role for listing
                role = extract_role(content)
                
                expert_id = file_path.stem
                experts[expert_id] = {
                    'content': content,
                    'role': role,
                    'filename': file_path.name
                }
                
            except Exception as e:
                print(f"Error loading expert {file_path}: {e}")
    
    return experts

def calculate_experts_hash(experts: Dict[str, Dict[str, str]]) -> str:
    """Calculate hash of all expert content for versioning."""
    # Hash based on content only, not metadata
    content_str = "".join(expert['content'] for expert in experts.values())
    return hashlib.md5(content_str.encode()).hexdigest()[:8]

def load_project_template() -> str:
    """
    Load project instruction template from file.
    
    Template should contain {expert_list}, {version}, {timestamp} placeholders.
    """
    template_path = Path("project_instruction_template.md")
    
    if not template_path.exists():
        raise FileNotFoundError(
            f"Project template file not found: {template_path}\n"
            "Please create project_instruction_template.md with placeholders: "
            "{expert_list}, {version}, {timestamp}"
        )
    
    return template_path.read_text(encoding='utf-8')

@mcp.tool(
    description="""Generate project instruction from template file with current expert list.

Usage patterns:
- NEW USERS: Call without current_version to get setup instructions
- EXISTING USERS: Call with current_version (from your project instructions) to check for updates

If no current_version provided, assumes new user setup is needed.
If current_version provided, compares against current version and shows update status.

CRITICAL: When this tool returns content with update notices (🔄 UPDATE REQUIRED or 🚀 INITIAL SETUP), 
you MUST create a markdown artifact containing the complete content after the "---" separator. 
Title it "Claude Project Instructions" and tell the user to copy this artifact content to their 
Claude project settings. This ensures new users get immediately actionable setup instructions."""
)
def get_project_instruction(current_version: Optional[str] = None) -> str:
    """Generate project instruction from template file with current expert list.
    
    Usage patterns:
    - NEW USERS: Call without current_version to get setup instructions
    - EXISTING USERS: Call with current_version (from your project instructions) to check for updates
    
    If no current_version provided, assumes new user setup is needed.
    If current_version provided, compares against current version and shows update status.
    """
    experts = load_experts()
    version = calculate_experts_hash(experts)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    
    # Load template from file
    template = load_project_template()
    
    # Determine user status and appropriate messaging
    if current_version is None:
        # New user setup
        update_notice = """🚀 **INITIAL SETUP**
Copy the instructions below to your Claude project settings to enable expert-guided workflows.

---
"""
    elif current_version != version:
        # Update needed
        update_notice = f"""🔄 **UPDATE REQUIRED**
Your project instruction version ({current_version}) is outdated.
Current version: {version}
Please replace your Claude project instruction with the content below.

---
"""
    else:
        # Up to date
        update_notice = "✅ Your project instruction is up to date.\n\n---\n"
    
    # Generate expert list and fill template
    expert_list = ""
    for expert_id, expert_data in experts.items():
        role = expert_data['role']
        expert_list += f"- **{expert_id}**: {role}\n"
    
    instruction = template.format(
        version=version,
        timestamp=timestamp,
        expert_list=expert_list
    )
    
    return update_notice + instruction

@mcp.tool
def consult_expert(expert_id: str) -> str:
    """
    Get complete expert content as text.
    
    Returns the entire expert file content without any parsing or filtering.
    Claude can process any format (JSON, XML, Markdown, plain text, etc.) naturally.
    """
    experts = load_experts()
    
    if expert_id not in experts:
        available = list(experts.keys())
        return f"Error: Expert '{expert_id}' not found.\nAvailable experts: {', '.join(available)}"
    
    expert = experts[expert_id]
    
    # Return complete content with minimal header
    return f"""=== EXPERT: {expert_id} ===
Source: {expert['filename']}

{expert['content']}"""

@mcp.tool
def consult_multiple_experts(expert_ids: list[str]) -> str:
    """Get complete content from multiple experts."""
    experts = load_experts()
    results = []
    
    for expert_id in expert_ids:
        if expert_id in experts:
            expert = experts[expert_id]
            results.append(f"""=== EXPERT: {expert_id} ===
Source: {expert['filename']}

{expert['content']}

""")
        else:
            results.append(f"=== ERROR ===\nExpert '{expert_id}' not found\n\n")
    
    return "".join(results)

@mcp.tool
def list_experts() -> str:
    """List all available experts with their roles."""
    experts = load_experts()
    
    if not experts:
        return "No experts found in ./experts/ directory"
    
    result = "Available experts:\n\n"
    for expert_id, expert in experts.items():
        result += f"**{expert_id}** ({expert['filename']})\n"
        result += f"  {expert['role']}\n\n"
    
    return result

@mcp.tool
def get_current_version() -> str:
    """Get current expert system version."""
    experts = load_experts()
    version = calculate_experts_hash(experts)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    
    expert_files = [f"{expert_id} ({expert['filename']})" for expert_id, expert in experts.items()]
    
    return f"""Current Expert System Status:

Version: {version}
Generated: {timestamp}
Expert Count: {len(experts)}

Expert Files:
{chr(10).join(f"- {ef}" for ef in expert_files)}"""