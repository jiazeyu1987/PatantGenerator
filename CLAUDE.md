# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **automated patent generation system** (自动专利生成系统) that uses Claude LLM to generate Chinese invention patents. The system supports two input modes and implements a dual-role multi-round iterative workflow.

### Core Architecture

- **Dual-role workflow**: Patent Writer (撰写专家) + Patent Reviewer (合规评审专家)
- **Multi-round iteration**: Each round consists of writing + review phases
- **Two input modes**: Code analysis or idea-based generation
- **Output**: Markdown patent documents with optional DOCX generation

## Common Development Commands

### Backend Development

```bash
# Navigate to backend directory
cd backend

# Install dependencies
pip install -r requirements.txt

# Start development server
python app.py

# Start with specific configuration
export LOG_LEVEL=DEBUG
python app.py
```

### Frontend Development

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Environment Setup

**Required environment variables:**
```bash
# Anthropic API key (for SDK mode)
export ANTHROPIC_API_KEY="your-api-key-here"

# Optional: LLM command (for CLI mode - deprecated)
export LLM_CMD="claude chat --model claude-3-5-sonnet"

# Optional: Configuration file path
export CONFIG_PATH="path/to/config.yaml"
```

## System Architecture

### Backend Components (`backend/`)

- **`app.py`**: Main Flask application and API endpoints
  - POST `/api/generate`: Main patent generation endpoint (synchronous)
  - POST `/api/generate/async`: Async patent generation with task polling
  - GET `/api/tasks/<task_id>`: Task status polling
  - serves frontend static files from `frontend/dist`

- **`patent_workflow.py`**: Core dual-role iteration engine
  - `run_patent_iteration()`: Orchestrates multi-round workflow
  - `build_writer_prompt()` / `build_reviewer_prompt()`: Prompt construction
  - Simple prompt engine for user custom prompts with `</text>` dynamic replacement
  - Outputs structured Chinese patent documents

- **`llm_client.py`**: LLM interface supporting both SDK and CLI modes
  - `call_llm_with_sdk()`: Anthropic Python SDK integration (recommended)
  - `call_llm_with_cli()`: CLI command wrapper (backward compatibility)
  - Intelligent prompt compression for length limits
  - Comprehensive error handling and retry logic

- **`code_analyzer.py`**: Codebase analysis and context building
  - Recursive file scanning with configurable limits
  - Supports: `.py,.js,.jsx,.ts,.tsx,.java,.cs,.go,.rs,.cpp,.c,.rb,.php`
  - Ignores: `node_modules,.git,dist,build,out,.next,.turbo,coverage`
  - Extracts first 80 lines for context generation

- **`template_manager.py`**: DOCX template management
- **`conversation_db.py`**: Conversation history persistence
- **`user_prompt_manager.py`**: Custom prompt management
- **`task_manager.py`**: Async task processing with status tracking

### Frontend Components (`frontend/`)

- **React + Vite** application with Ant Design components
- **`src/PatentApp.jsx`**: Main application component
- **`src/TemplateSelector.jsx`**: Template selection interface
- **`src/ConversationViewer.jsx`**: Conversation history viewer
- **`src/App.jsx`**: Core UI components and API integration

### Input Modes

1. **Code Mode**: Automatically analyzes codebase to extract innovations
2. **Idea Mode**: Direct text input for technical concepts/requirements

### Output Structure

Generated patents include these sections (in Chinese):
- 标题 (Title)
- 技术领域 (Technical Field)
- 背景技术 (Background Art)
- 发明内容 (Summary of Invention)
- 附图说明 (Brief Description of Drawings) - Supports mermaid syntax
- 具体实施方式 (Detailed Description)
- 权利要求书 (Claims)
- 摘要 (Abstract)

## Key Implementation Details

### Patent Generation Workflow

The system implements a sophisticated multi-round process in `patent_workflow.py:390`:

1. **Template Selection**: Load and analyze DOCX template if specified
2. **Multi-round Iteration**:
   - Writer Phase: Generates/refines patent draft based on context and reviews
   - Reviewer Phase: Analyzes draft for compliance, risks, and improvements
   - Progress tracking and database logging of each round
3. **Output Generation**: Saves final markdown and optionally generates DOCX

### Custom Prompt System

Users can provide custom prompts with dynamic variable replacement:
- `</text>` marker for dynamic patent draft injection
- `{{context}}`, `{{iteration}}`, `{{total_iterations}}` variable placeholders
- Strict mode for 100% user prompt preservation
- Fallback to system defaults when custom prompts are empty

### Code Analysis Strategy

The code analyzer (`code_analyzer.py`) creates lightweight context by:
- Sampling diverse code files across the project (200 file limit)
- Reading first 80 lines to capture structure and logic
- Building markdown overview for LLM processing
- Respecting ignore patterns and file size limits

### LLM Integration Patterns

The system supports two LLM integration modes:

1. **SDK Mode (Recommended)**: Uses Anthropic Python SDK
   - Better error handling and rate limiting
   - Automatic retry with exponential backoff
   - Structured response parsing

2. **CLI Mode (Legacy)**: Executes command-line LLM tools
   - Maintained for backward compatibility
   - Enhanced security validation
   - Process isolation and timeout protection

### Database Schema

Conversation tracking (`conversation_db.py`):
- Tasks table: Generation metadata and status
- Conversation_rounds table: Per-round writer/reviewer interactions
- SQLite database with automatic schema migration

## Development Notes

### Testing the System

1. Ensure `ANTHROPIC_API_KEY` environment variable is properly configured
2. Install backend dependencies: `cd backend && pip install -r requirements.txt`
3. Install frontend dependencies: `cd frontend && npm install`
4. Start backend server: `python app.py` (listens on http://localhost:8081)
5. Test both code and idea modes with different iteration counts

### Configuration Options

Key configuration in `config.py`:
- **LLM Settings**: Model selection, token limits, retry logic, SDK/CLI mode
- **File Analysis**: Max files, sizes, supported extensions
- **Task Management**: Worker count, timeouts, cleanup intervals
- **Server**: Host/port configuration, debug mode, threading
- **Security**: Command validation, input sanitization

### Error Handling

The system implements comprehensive error handling:
- LLM API rate limiting and quota management
- Input validation and sanitization
- File system access permissions
- Graceful degradation for missing components
- Structured logging with configurable levels

## Advanced Features

### Template System

- DOCX template management with validation
- Template complexity and quality scoring
- Intelligent template-section mapping
- Fallback to pure markdown when templates fail

### Async Processing

- Background task processing with status polling
- Configurable worker pools and timeouts
- Task cancellation and cleanup
- Progress tracking with real-time updates

### Conversation History

- Complete interaction logging for transparency
- Round-by-round writer/reviewer dialogue storage
- Task metadata and configuration tracking
- Web interface for conversation review

### Custom Prompt Engine

- User-defined writer and reviewer prompts
- Dynamic content replacement with `</text>` markers
- Variable substitution with `{{variable}}` syntax
- Strict execution mode vs. enhanced mode

## Security Considerations

- Command injection prevention in CLI mode
- Input validation and sanitization
- File access restrictions and path validation
- API key protection and secure storage
- Rate limiting and quota management

## Performance Optimization

- Intelligent prompt compression to fit token limits
- Async processing for long-running tasks
- Database connection pooling
- Static file serving optimization
- Configurable caching strategies