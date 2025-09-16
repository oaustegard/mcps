from fastmcp import FastMCP
from pathlib import Path
import hashlib
from datetime import datetime
from typing import Dict, Optional, Callable, Any
from functools import wraps
import re

# ============================================================================
# MODULE-LEVEL CONSTANTS AND CACHING
# ============================================================================

# Cache for experts data and version - calculated once at startup
_EXPERTS_CACHE: Optional[Dict[str, Dict[str, str]]] = None
_CURRENT_VERSION: Optional[str] = None

def _initialize_experts_cache() -> tuple[Dict[str, Dict[str, str]], str]:
    """
    Initialize experts cache and calculate version hash.
    
    Called once at module load time for optimal performance.
    
    Returns:
        tuple: (experts_dict, version_hash)
    """
    experts = {}
    experts_dir = Path("experts")
    
    # Create directory if it doesn't exist
    if not experts_dir.exists():
        experts_dir.mkdir()
        print("Created ./experts/ directory. Add your expert files here!")
        return experts, "empty"
    
    # Load ALL text files (any extension)
    text_extensions = {'.txt', '.md', '.json', '.xml', '.yaml', '.yml', '.py', '.js', '.html'}
    
    for file_path in experts_dir.iterdir():
        if file_path.is_file() and (file_path.suffix.lower() in text_extensions or not file_path.suffix):
            try:
                # Read entire file as text
                content = file_path.read_text(encoding='utf-8')
                
                # Extract role for listing
                role = _extract_role(content)
                
                expert_id = file_path.stem
                experts[expert_id] = {
                    'content': content,
                    'role': role,
                    'filename': file_path.name
                }
                
            except Exception as e:
                print(f"Error loading expert {file_path}: {e}")
    
    # Calculate version hash based on content
    if experts:
        content_str = "".join(expert['content'] for expert in experts.values())
        version_hash = hashlib.md5(content_str.encode()).hexdigest()[:8]
    else:
        version_hash = "empty"
    
    return experts, version_hash

def get_cached_experts() -> Dict[str, Dict[str, str]]:
    """
    Get cached experts data, initializing if necessary.
    
    Returns:
        Dict: Cached experts data
    """
    global _EXPERTS_CACHE, _CURRENT_VERSION
    
    if _EXPERTS_CACHE is None:
        _EXPERTS_CACHE, _CURRENT_VERSION = _initialize_experts_cache()
    
    return _EXPERTS_CACHE

def get_current_version() -> str:
    """
    Get current cached version, initializing if necessary.
    
    Returns:
        str: Current version hash
    """
    global _EXPERTS_CACHE, _CURRENT_VERSION
    
    if _CURRENT_VERSION is None:
        _EXPERTS_CACHE, _CURRENT_VERSION = _initialize_experts_cache()
    
    return _CURRENT_VERSION

# ============================================================================
# VERSION CHECKING INFRASTRUCTURE
# ============================================================================

def check_version_compatibility(provided_version: Optional[str]) -> Optional[str]:
    """
    Check if provided version matches current version.
    
    Args:
        provided_version: Version string from client, or None
        
    Returns:
        None if versions match, or project instruction update string if mismatch
    """
    current_version = get_current_version()
    
    # If no version provided or version mismatch, return update instructions
    if provided_version is None or provided_version != current_version:
        return _generate_project_instruction_update(provided_version, current_version)
    
    return None

def version_check(func: Callable) -> Callable:
    """
    Decorator that adds automatic version checking to tool functions.
    
    If version is missing or outdated, returns project instruction update
    instead of executing the tool function.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Extract version from kwargs if present
        version = kwargs.get('version')
        
        # Check version compatibility
        version_update = check_version_compatibility(version)
        if version_update:
            return version_update
        
        # Remove version from kwargs before calling original function
        # (since original functions don't expect this parameter)
        filtered_kwargs = {k: v for k, v in kwargs.items() if k != 'version'}
        
        return func(*args, **filtered_kwargs)
    
    return wrapper

def _generate_project_instruction_update(provided_version: Optional[str], current_version: str) -> str:
    """
    Generate project instruction update message.
    
    Args:
        provided_version: Version provided by client (may be None)
        current_version: Current server version
        
    Returns:
        str: Project instruction update message
    """
    experts = get_cached_experts()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    
    # Load template from file
    try:
        template = _load_project_template()
    except FileNotFoundError as e:
        return f"❌ Configuration Error: {e}"
    
    # Determine update type
    if provided_version is None:
        update_notice = """
🚀 **VERSION CHECK: INITIAL SETUP REQUIRED**

Your Claude project is missing version information. Please copy the instructions below 
to your Claude project settings to enable version-aware expert consultations.

---
"""
    else:
        update_notice = f"""
🔄 **VERSION CHECK: UPDATE REQUIRED**

Your project instruction version ({provided_version}) is outdated.
Current server version: {current_version}

Please replace your Claude project instruction with the content below to ensure 
compatibility with the latest expert knowledge.

---
"""
    
    # Generate expert list
    expert_list = ""
    for expert_id, expert_data in experts.items():
        role = expert_data['role']
        expert_list += f"- **{expert_id}**: {role}\n"
    
    # Fill template
    instruction = template.format(
        version=current_version,
        timestamp=timestamp,
        expert_list=expert_list
    )
    
    return update_notice + instruction

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def _extract_role(content: str) -> str:
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

def _load_project_template() -> str:
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

# ============================================================================
# FASTMCP SERVER CONFIGURATION
# ============================================================================

mcp = FastMCP(
    name="ICL Experts",
    instructions="""In-Context Learning (ICL) Experts providing specialized domain knowledge.

🔄 **SERVER AVAILABILITY NOTICE**: This server runs on a serverless platform with cold starts.
If ANY tool call fails with connection/timeout errors:
1. Wait 2-3 seconds for server initialization
2. Retry the EXACT same tool call once 
3. If second attempt fails, try the wakeup_server() tool, then retry your original call
4. If still failing after wakeup, inform user of temporary unavailability

🆔 **VERSION MANAGEMENT**: All tools accept an optional 'version' parameter for automatic 
project instruction updates. If your project instructions are missing version info or 
outdated, tools will return update instructions instead of normal responses.

IMPORTANT: If a user asks about ICL Experts usage, setup, or configuration, 
ALWAYS call get_project_instruction() first (without version parameter) to provide current setup instructions, 
then explain usage (deep insights can be provided by the experts_README expert). This ensures new users get 
immediately actionable setup instructions.

For expert consultations, use consult_expert(expert_id) or consult_multiple_experts([ids]).
For expert discovery, use list_experts().

**Retry Pattern Example**:
1. Call consult_expert("python_specialist") → fails
2. Wait 2-3 seconds
3. Call consult_expert("python_specialist") again → should succeed
4. If still failing, call wakeup_server() then retry original call"""
)

# ============================================================================
# TOOL DEFINITIONS
# ============================================================================

@mcp.tool(
    description="""🔄 Wakeup tool to initialize the serverless environment. 
    
    Call this tool if other ICL Expert tools are failing with connection/timeout errors.
    After calling this, retry your original tool call. This tool simply ensures the 
    server is active and ready to process requests.
    
    Usage: Call wakeup_server() → wait 1-2 seconds → retry your original tool call."""
)
def wakeup_server() -> str:
    """Lightweight ping to warm serverless container."""
    return """✅ Server initialization complete. 

🔄 **Next Steps**: 
1. Wait 1-2 seconds for full initialization
2. Retry your original tool call (consult_expert, list_experts, etc.)
3. The server should now respond successfully

If you continue experiencing issues after this wakeup call, the server may be experiencing temporary problems."""

@mcp.tool(
    description="""Generate project instruction from template file with current expert list.

⚠️ **Retry Notice**: If this tool fails initially, wait 2-3 seconds and retry once.

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
def get_project_instruction(current_version: Optional[str] = None, version: Optional[str] = None) -> str:
    """
    Generate project instruction with template substitution.
    
    Args:
        current_version: Legacy parameter for backward compatibility
        version: Current project instruction version for auto-update checking
    """
    # Use current_version if provided, otherwise use version parameter
    check_version = current_version or version
    
    experts = get_cached_experts()
    current_ver = get_current_version()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    
    # Load template from file
    try:
        template = _load_project_template()
    except FileNotFoundError as e:
        return f"❌ Configuration Error: {e}"
    
    # Determine user status and appropriate messaging
    if check_version is None:
        # New user setup
        update_notice = """🚀 **INITIAL SETUP**
Copy the instructions below to your Claude project settings to enable expert-guided workflows.

---
"""
    elif check_version != current_ver:
        # Update needed
        update_notice = f"""🔄 **UPDATE REQUIRED**
Your project instruction version ({check_version}) is outdated.
Current version: {current_ver}
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
        version=current_ver,
        timestamp=timestamp,
        expert_list=expert_list
    )
    
    return update_notice + instruction

@mcp.tool(
    description="""Get complete expert content as text.
    
    ⚠️ **Retry Notice**: If this tool fails initially, wait 2-3 seconds and retry once, 
    or use wakeup_server() first.
    
    🆔 **Version Check**: Include 'version' parameter from your project instructions for 
    automatic update notifications.
    
    Returns the entire expert file content without any parsing or filtering.
    Claude can process any format (JSON, XML, Markdown, plain text, etc.) naturally."""
)
@version_check
def consult_expert(expert_id: str) -> str:
    """Return complete expert file content from cache."""
    experts = get_cached_experts()
    
    if expert_id not in experts:
        available = list(experts.keys())
        return f"Error: Expert '{expert_id}' not found.\nAvailable experts: {', '.join(available)}"
    
    expert = experts[expert_id]
    
    # Return complete content with minimal header
    return f"""=== EXPERT: {expert_id} ===
Source: {expert['filename']}

{expert['content']}"""

@mcp.tool(
    description="""Get complete content from multiple experts.
    
    ⚠️ **Retry Notice**: If this tool fails initially, wait 2-3 seconds and retry once,
    or use wakeup_server() first.
    
    🆔 **Version Check**: Include 'version' parameter from your project instructions for 
    automatic update notifications."""
)
@version_check
def consult_multiple_experts(expert_ids: list[str]) -> str:
    """Return concatenated content from multiple expert files."""
    experts = get_cached_experts()
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

@mcp.tool(
    description="""List all available experts with their roles.
    
    ⚠️ **Retry Notice**: If this tool fails initially, wait 2-3 seconds and retry once,
    or use wakeup_server() first.
    
    🆔 **Version Check**: Include 'version' parameter from your project instructions for 
    automatic update notifications."""
)
@version_check
def list_experts() -> str:
    """Format cached expert metadata for display."""
    experts = get_cached_experts()
    
    if not experts:
        return "No experts found in ./experts/ directory"
    
    result = "Available experts:\n\n"
    for expert_id, expert in experts.items():
        result += f"**{expert_id}** ({expert['filename']})\n"
        result += f"  {expert['role']}\n\n"
    
    return result

@mcp.tool(
    description="""Get current expert system version and status.
    
    ⚠️ **Retry Notice**: If this tool fails initially, wait 2-3 seconds and retry once,
    or use wakeup_server() first.
    
    🆔 **Version Check**: Include 'version' parameter from your project instructions for 
    automatic update notifications."""
)
@version_check
def get_expert_system_status() -> str:
    """Return system status with cache performance indicators."""
    experts = get_cached_experts()
    version = get_current_version()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    
    expert_files = [f"{expert_id} ({expert['filename']})" for expert_id, expert in experts.items()]
    
    return f"""Current Expert System Status:

Version: {version}
Generated: {timestamp}
Expert Count: {len(experts)}

Expert Files:
{chr(10).join(f"- {ef}" for ef in expert_files)}

🔄 **Performance**: Expert data cached at startup for optimal response times
✅ **Version Management**: Automatic project instruction updates enabled"""

# Initialize cache at module load time for optimal performance
_EXPERTS_CACHE, _CURRENT_VERSION = _initialize_experts_cache()