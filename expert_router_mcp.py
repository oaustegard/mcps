# /// script
# dependencies = [
#     "fastmcp>=2.0.0",
#     "thefuzz>=0.19.0",
# ]
# ///
from fastmcp import FastMCP
from pathlib import Path
import hashlib
from typing import Dict, Optional
import re
from thefuzz import fuzz, process

# ============================================================================
# MODULE-LEVEL CONSTANTS AND CACHING
# ============================================================================

# Cache for experts data - calculated once at startup
_EXPERTS_CACHE: Optional[Dict[str, Dict[str, str]]] = None

def _initialize_experts_cache() -> Dict[str, Dict[str, str]]:
    """
    Initialize experts cache for optimal performance.
    
    Called once at module load time.
    
    Returns:
        Dict: experts_dict with expert_id -> {content, role, filename}
    """
    experts = {}
    experts_dir = Path("experts")
    
    # Create directory if it doesn't exist
    if not experts_dir.exists():
        experts_dir.mkdir()
        print("Created ./experts/ directory. Add your expert files here!")
        return experts
    
    # Load ALL text files (any extension)
    text_extensions = {'.txt', '.md', '.json', '.xml', '.yaml', '.yml', '.py', '.js', '.html'}
    
    for file_path in experts_dir.iterdir():
        if file_path.is_file() and (file_path.suffix.lower() in text_extensions or not file_path.suffix):
            try:
                # Read entire file as text
                content = file_path.read_text(encoding='utf-8')
                
                # Extract role for listing and routing
                role = _extract_role(content)
                
                expert_id = file_path.stem
                experts[expert_id] = {
                    'content': content,
                    'role': role,
                    'filename': file_path.name
                }
                
            except Exception as e:
                print(f"Error loading expert {file_path}: {e}")
    
    return experts

def get_cached_experts() -> Dict[str, Dict[str, str]]:
    """
    Get cached experts data, initializing if necessary.
    
    Returns:
        Dict: Cached experts data
    """
    global _EXPERTS_CACHE
    
    if _EXPERTS_CACHE is None:
        _EXPERTS_CACHE = _initialize_experts_cache()
    
    return _EXPERTS_CACHE

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

def _generate_expert_system_context() -> str:
    """
    Generate dynamic system context for automatic expert routing.
    
    This replaces static project instructions with dynamic MCP context.
    """
    experts = get_cached_experts()
    
    if not experts:
        return """
You have access to specialized experts via ICL Experts MCP, but no experts are currently loaded.
Check that expert files exist in the ./experts/ directory.
"""
    
    # Generate expert descriptions for routing
    expert_descriptions = []
    for expert_id, expert_data in experts.items():
        role = expert_data['role']
        expert_descriptions.append(f"- **{expert_id}**: {role}")
    
    expert_list = "\n".join(expert_descriptions)
    
    return f"""
🎯 **ICL EXPERTS SYSTEM CONTEXT**

You have access to {len(experts)} specialized experts for domain-specific knowledge. Your goal is to
automatically consult them to answer user questions without the user needing to know about this system.

**AVAILABLE EXPERTS**
{expert_list}

**USAGE PATTERNS**
1.  **Automatic Expert Consultation**: When a user asks a question in a specific domain (e.g., "How do I write a Java class?"), silently consult the relevant expert (`consult_expert("java_specialist")`) and use the retrieved knowledge to formulate your answer. The user should feel like they are talking to a single, highly knowledgeable assistant.

2.  **Multi-Expert Synthesis**: For complex questions that span multiple domains (e.g., "How do I analyze data with a Python script?"), consult multiple experts (`consult_multiple_experts(["python_specialist", "data_analysis"])`) and synthesize their knowledge into a single, comprehensive answer.

3.  **Seamless Integration**: Do not mention the expert system unless there is an error. The process should be invisible to the user. Simply apply the expert's knowledge to provide a better answer.

**ROUTING GUIDANCE**
-   **Analyze User Intent**: Determine the primary domain of the user's question.
-   **Select the Best Expert**: Choose the expert whose role best matches the user's intent.
-   **Consult and Answer**: Call the appropriate tool, wait for the expert knowledge, and then formulate your response.

Your primary instruction is to use these experts to provide the most accurate and specialized answers possible, creating a seamless and powerful user experience.
"""

# ============================================================================
# FASTMCP SERVER CONFIGURATION
# ============================================================================

# Generate dynamic system context
expert_system_context = _generate_expert_system_context()

mcp = FastMCP(
    name="ICL Experts",
    instructions=f"""{expert_system_context}

🔄 **SERVER AVAILABILITY NOTICE**: This server runs on a serverless platform with cold starts.
If ANY tool call fails with connection/timeout errors:
1. Wait 2-3 seconds for server initialization
2. Retry the EXACT same tool call once 
3. If second attempt fails, try the wakeup_server() tool, then retry your original call
4. If still failing after wakeup, inform user of temporary unavailability

**Retry Pattern Example**:
1. Call consult_expert("python_specialist") → fails
2. Wait 2-3 seconds
3. Call consult_expert("python_specialist") again → should succeed
4. If still failing, call wakeup_server() then retry original call"""
)

# ============================================================================
# SIMPLIFIED TOOL DEFINITIONS
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
    description="""Consult a specialized expert for domain-specific knowledge, with smart routing.

    - If you provide an exact expert_id, it will be returned.
    - If the expert_id is not found, this tool will automatically find the best match.
    - Example: consult_expert("python") will route to "python_specialist".
    
    ⚠️ **Retry Notice**: If this tool fails, wait 2-3 seconds and retry, or use wakeup_server()."""
)
def consult_expert(expert_id: str) -> str:
    """
    Return complete expert file content from cache with fuzzy matching.
    """
    experts = get_cached_experts()
    
    # 1. Exact match (fast path)
    if expert_id in experts:
        expert = experts[expert_id]
        return f"""=== EXPERT: {expert_id} ===
Source: {expert['filename']}

{expert['content']}"""

    # 2. Fuzzy matching for intelligent routing
    available_experts = list(experts.keys())
    if not available_experts:
        return "Error: No experts available to consult."

    # Find the best match
    best_match, score = process.extractOne(expert_id, available_experts, scorer=fuzz.WRatio)
    
    # 3. Auto-consult if high confidence, otherwise suggest
    if best_match and score > 80:
        # Automatically route to the best match
        expert = experts[best_match]
        return f"""=== EXPERT: {best_match} (Auto-routed from '{expert_id}') ===
Source: {expert['filename']}

{expert['content']}"""
    elif best_match and score > 50:
        # Suggest a close match
        return f"Error: Expert '{expert_id}' not found. Did you mean '{best_match}'?"
    else:
        # Generic not found error with list
        return f"Error: Expert '{expert_id}' not found.\nAvailable experts: {', '.join(available_experts)}"

@mcp.tool(
    description="""Get complete content from multiple experts.
    
    ⚠️ **Retry Notice**: If this tool fails initially, wait 2-3 seconds and retry once,
    or use wakeup_server() first."""
)
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
    or use wakeup_server() first."""
)
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

# Initialize cache at module load time for optimal performance
_EXPERTS_CACHE = _initialize_experts_cache()