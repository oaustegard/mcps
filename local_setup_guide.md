# ICL Experts - Local Setup Guide

This guide shows how to run ICL Experts locally using FastMCP.

## Quick Start (Recommended)

The simplest approach uses the FastMCP CLI directly:

### 1. Install FastMCP
```bash
# Using uv (recommended)
uv pip install fastmcp

# Or using pip  
pip install fastmcp
```

### 2. Get ICL Experts
```bash
# Download or clone the ICL Experts files
# You need: expert_router_mcp.py and project_instruction_template.md
```

### 3. Create Experts Directory
```bash
mkdir experts
# Add your expert files here (see expert creation guide)
```

### 4. Test the Server
```bash
# Test that the server runs
fastmcp run expert_router_mcp.py:mcp

# You should see: "ICL Experts MCP server running..."
# Press Ctrl+C to stop
```

### 5. Configure Claude Desktop

Add to your Claude Desktop MCP settings file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "icl-experts": {
      "command": "fastmcp",
      "args": ["run", "/full/path/to/your/expert_router_mcp.py:mcp"]
    }
  }
}
```

**Important**: Use the full absolute path to your `expert_router_mcp.py` file.

### 6. Restart Claude Desktop

After saving the configuration, restart Claude Desktop completely.

### 7. Test the Connection

In Claude, try asking:
- "List available experts"
- "What experts do you have access to?"

Claude should use the `list_experts()` tool and show your available experts.

## Alternative: Package Installation

If you prefer a more permanent installation:

### 1. Create Package Files

Create these additional files in your ICL Experts directory:

**pyproject.toml**:
```toml
[build-system]
requires = ["setuptools>=61", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "icl-experts"
version = "1.0.0"
dependencies = ["fastmcp>=2.11.0"]

[project.scripts]
icl-experts = "expert_router_mcp:main"
```

**Add to expert_router_mcp.py**:
```python
# Add this function at the end of expert_router_mcp.py
def main():
    """Entry point for package installation."""
    mcp.run()

if __name__ == "__main__":
    main()
```

### 2. Install the Package
```bash
cd /path/to/icl-experts
pip install -e .
```

### 3. Configure Claude
```json
{
  "mcpServers": {
    "icl-experts": {
      "command": "icl-experts",
      "args": []
    }
  }
}
```

## Troubleshooting

### Server Won't Start
```bash
# Check FastMCP installation
fastmcp version

# Test the server file directly
python expert_router_mcp.py

# Check for syntax errors
python -m py_compile expert_router_mcp.py
```

### Claude Can't Connect
1. **Check the file path**: Use absolute path in MCP config
2. **Verify configuration**: JSON syntax must be exact
3. **Restart Claude**: Must restart after config changes
4. **Check permissions**: Ensure files are readable
5. **Test manually**: Run `fastmcp run expert_router_mcp.py:mcp` first

### "Expert not found" Errors
1. **Check experts directory**: Must be named `experts/`
2. **Verify file extensions**: Use `.txt`, `.md`, `.xml`, `.json`, etc.
3. **Test loading**: Look for error messages when server starts
4. **Check file names**: Expert ID = filename without extension

### Expert Roles Not Detected
1. **Add role definition**: Use `<role>...</role>` tags
2. **Check format**: See expert creation guide for patterns
3. **Test extraction**: Role should show in `list_experts()` output

## Expert Creation Quick Reference

Create files in the `experts/` directory with role definitions:

**XML (Recommended)**:
```xml
<role>
You are a [domain] specialist who [does what].
</role>

<expertise_areas>
- Skill 1
- Skill 2
</expertise_areas>

<!-- Additional expert content -->
```

**JSON**:
```json
{
  "system_prompt": "You are a [domain] expert...",
  "expertise": ["skill1", "skill2"],
  "methodology": "Your approach..."
}
```

**Markdown**:
```markdown
# Role
You are a [domain] specialist...

## Expertise
- Skill 1
- Skill 2
```

**Plain Text**:
```
ROLE: You are a [domain] expert specializing in [area].

APPROACH:
- Key principle 1
- Key principle 2
```

## HTTP Server (Optional)

For remote access or testing, you can run an HTTP server:

```bash
# Run with HTTP transport
fastmcp run expert_router_mcp.py:mcp --transport http --port 8000

# Test with curl
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/list"}'
```

## Next Steps

1. **Create your first expert**: Add a file to `experts/` directory
2. **Test consultation**: Ask Claude to consult your expert
3. **Generate project instruction**: Ask Claude for updated project instructions
4. **Add more experts**: Build your expert knowledge base
5. **Share with team**: Use version control for expert files

The system is designed for rapid iteration - just add/modify expert files and they're immediately available!