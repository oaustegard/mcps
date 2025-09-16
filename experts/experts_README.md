# ICL Experts System

**Description**: This is the complete documentation for the ICL Experts system - an MCP server that provides Claude with access to specialized expert knowledge. This file serves as both user documentation and LLM context for system-related questions. The experts themselves are the other files in this directory.

## What This System Does

The ICL Experts system provides Claude with access to specialized domain knowledge through text files stored in the `./experts/` directory. Each expert file becomes a consultable knowledge base that Claude can use to provide specialized guidance.

**Key Capabilities:**
- **Dynamic Expert Loading**: Any text file in this directory becomes an expert
- **Flexible Formats**: Supports .txt, .md, .json, .xml, .yaml, and any plain text format
- **Multi-Expert Consultation**: Can combine insights from multiple experts
- **Automatic Role Extraction**: Identifies expert specializations for easy discovery
- **Version Management**: Tracks changes and notifies users of updates

## Available Tools

When connected to the ICL Experts MCP server, Claude has access to these tools:

### `consult_expert(expert_id)`
Get complete knowledge from a specific expert. The `expert_id` is the filename without extension.

```python
# Example: consult the Python specialist
expert_knowledge = consult_expert("python_specialist")
```

### `consult_multiple_experts(expert_ids)`
Consult several experts simultaneously for cross-domain problems.

```python
# Example: get insights from multiple experts
multi_expert_knowledge = consult_multiple_experts(["data_analysis", "python_specialist"])
```

### `list_experts()`
Show all available experts with their role descriptions.

### `get_current_version()`
Display system version and expert inventory.

### `get_project_instruction(current_version=None)`
Generate or update Claude project instructions:
- **No version provided**: Get initial setup instructions (new user)
- **Version provided**: Check for updates (existing user)

## How It Works

1. **Expert Storage**: Each text file in this directory is an expert
2. **Role Detection**: System automatically extracts role descriptions using multiple patterns
3. **Content Access**: When consulted, entire file content is provided to Claude
4. **Knowledge Application**: Claude applies expert methodology and knowledge to responses

## Usage Patterns

### First-Time Setup
```python
# User asks about ICL Experts → System calls automatically:
get_project_instruction()  # No version = setup instructions
```

### Regular Usage
```python
# User asks domain-specific question → Claude calls relevant expert:
consult_expert("java_specialist")  # For Java questions
consult_expert("data_analysis")   # For data science questions
```

### Multi-Domain Problems
```python
# Complex problems spanning domains:
consult_multiple_experts(["python_specialist", "data_analysis"])
```

### Update Checking
```python
# Check if project instructions need updating:
get_project_instruction(current_version="abc12345")
```

## Expert File Requirements

### Supported Formats
- `.txt`, `.md`, `.json`, `.xml`, `.yaml`, `.yml`
- `.py`, `.js`, `.html` (any plain text file)
- Files without extensions are also supported

### Role Definition
Each expert should include a role definition for automatic extraction. Supported patterns:

```xml
<role>You are a [domain] specialist who...</role>
```

```json
{"system_prompt": "You are a [domain] expert who..."}
```

```markdown
# Role
You are a [domain] specialist who...
```

```text
ROLE: You are a [domain] expert who...
```

### Content Structure
- **Role**: What the expert specializes in
- **Methodology**: How the expert approaches problems  
- **Knowledge Base**: Domain-specific information, tools, patterns
- **Examples**: Practical applications and use cases

## Creating New Experts

### Basic Requirements
1. Create a text file in this directory
2. Include a clear role definition
3. Provide specialized knowledge relevant to the domain
4. Use any format you prefer (XML, JSON, Markdown, plain text)

### For Detailed Guidance
Consult the `prompt_expert` for comprehensive expert creation assistance, including:
- Structured role definitions
- Methodology frameworks
- Knowledge organization patterns
- Format-specific templates

## File Organization

```
experts/
├── README.md                 # This documentation
├── data_analysis.json        # Data science expertise
├── java_specialist.xml       # Java development knowledge
├── python_specialist.xml     # Python programming expertise
├── prompt_expert.xml         # Expert creation guidance
└── [other experts...]        # Domain-specific knowledge files
```

## System Integration

### Project Instructions
The system generates Claude project instructions that:
- List all available experts
- Include usage patterns
- Provide version information for update tracking
- Enable automatic expert consultation

### Automatic Onboarding
- New users automatically get setup instructions
- No manual configuration needed
- Version tracking ensures users stay current

## Troubleshooting

### "Expert not found" Error
- Verify file exists in `./experts/` directory
- Check filename matches `expert_id` (without extension)
- Ensure file is readable plain text

### Role Extraction Issues  
- Add role definition using supported patterns
- Use `<role>...</role>` tags for guaranteed extraction
- Check for syntax errors in role definition

### Expert Content Seems Limited
- Role extraction shows truncated content for listings (by design)
- Full content available when expert is consulted
- Use `consult_expert()` to access complete knowledge

### Version Mismatches
- Expert files changed since last project instruction generation
- Call `get_project_instruction()` to get updated instructions
- Replace Claude project settings with new content

## System Architecture

### Expert Loading
- Files loaded dynamically on each tool call
- Supports hot-swapping and updates without restart
- Any text file automatically becomes available

### Role Extraction
- Multiple pattern matching for maximum compatibility
- Prioritizes rich role content over simple descriptions  
- Fallback patterns ensure broad format support

### Version Management
- Hash calculated from all expert content
- Change any expert file to trigger version update
- Automatic update notifications in project instructions

## Performance Considerations

- Keep expert files focused and relevant
- Use clear, specific role definitions  
- Consider breaking very large experts into focused sub-experts
- Regular cleanup of unused experts

## Local Development

When running this as a local MCP server:

1. **Prerequisites**: Install FastMCP (`pip install fastmcp`)
2. **Run Server**: `fastmcp run expert_router_mcp.py:mcp`
3. **Expert Management**: Add/modify files in this directory
4. **Testing**: Use `list_experts()` to verify experts load correctly

The system automatically picks up changes to expert files without restart.

## Success Indicators

**Effective Usage:**
- Claude consistently identifies and consults relevant experts
- Expert responses demonstrate specialized knowledge
- Multi-expert consultations provide synthesized insights  
- Users receive value from domain-specific guidance

**System Health:**
- All expert files load without errors
- Role extraction works for all experts
- Project instructions stay current
- Expert knowledge remains focused and actionable