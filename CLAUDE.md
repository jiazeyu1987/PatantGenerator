# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **automated patent generation system** (自动专利生成系统) that uses Claude CLI to generate Chinese invention patents. The system supports two input modes and implements a dual-role multi-round iterative workflow.

### Core Architecture

- **Dual-role workflow**: Patent Writer (撰写专家) + Patent Reviewer (合规评审专家)
- **Multi-round iteration**: Each round consists of writing + review phases
- **Two input modes**: Code analysis or idea-based generation
- **Output**: Markdown patent documents with mermaid diagrams

## Common Development Commands

### Backend Development

```bash
# Navigate to backend directory
cd backend

# Install dependencies
npm install

# Start development server
npm run dev

# Start production server
npm start
```

### Environment Setup

**Required environment variable:**
```bash
# Configure Claude CLI command
export LLM_CMD="claude chat --model claude-3-5-sonnet"
# Windows equivalent:
set LLM_CMD=claude chat --model claude-3-5-sonnet
```

The LLM command must:
- Read prompts from standard input
- Write responses to standard output
- Exit with code 0 on success

## System Architecture

### Backend Components (`backend/`)

- **`server.js`**: Express HTTP server + static frontend hosting
  - POST `/api/generate`: Main patent generation endpoint
  - Handles both code and idea modes
  - Manages iteration workflow orchestration

- **`patentWorkflow.js`**: Core dual-role iteration engine
  - `buildWriterPrompt()`: Constructs prompts for patent writing
  - `buildReviewerPrompt()`: Constructs prompts for compliance review
  - `runPatentIteration()`: Orchestrates multi-round workflow
  - Outputs structured Chinese patent documents

- **`codeAnalyzer.js`**: Codebase analysis and context building
  - Recursive file scanning (200 file limit)
  - Supports: `.js,.jsx,.ts,.tsx,.py,.java,.cs,.go,.rs,.cpp,.c,.rb,.php`
  - Ignores: `node_modules,.git,dist,build,out,.next,.turbo,coverage`
  - Extracts first 80 lines for context generation

- **`llmClient.js`**: Claude CLI wrapper
  - Executes configured `LLM_CMD` via child process
  - Handles stdin/stdout communication
  - 20MB buffer limit for responses

### Frontend Components (`frontend/`)

- **`index.html`**: Main UI with mode selection and configuration
- **`main.js`**: Form handling and API communication
- **`style.css`**: Dark theme UI styling

### Input Modes

1. **Code Mode**: Automatically analyzes codebase to extract innovations
2. **Idea Mode**: Direct text input for technical concepts/requirements

### Output Structure

Generated patents include these sections (in Chinese):
- 标题 (Title)
- 技术领域 (Technical Field)
- 背景技术 (Background Art)
- 发明内容 (Summary of Invention)
- 附图说明 (Brief Description of Drawings) - **Uses mermaid syntax**
- 具体实施方式 (Detailed Description)
- 权利要求书 (Claims)
- 摘要 (Abstract)

## Key Implementation Details

### Patent Generation Workflow

The system implements a sophisticated multi-round process in `patentWorkflow.js:99`:

1. **Writer Phase**: Generates complete patent draft based on context and previous reviews
2. **Reviewer Phase**: Analyzes draft for compliance, risks, and improvement opportunities
3. **Iteration**: Refines draft over multiple rounds based on reviewer feedback
4. **Output**: Saves final markdown to `output/` directory with timestamp

### Code Analysis Strategy

The code analyzer (`codeAnalyzer.js:87`) creates lightweight context by:
- Sampling diverse code files across the project
- Reading first 80 lines to capture structure and logic
- Building markdown overview for LLM processing
- Focusing on technical innovation extraction

### CLI Integration Pattern

The LLM client (`llmClient.js:11`) uses a flexible command pattern:
- Environment-based configuration for different Claude CLI setups
- Process-based execution with proper error handling
- Stream-based communication for large responses

## Development Notes

### Testing the System

1. Ensure `LLM_CMD` environment variable is properly configured
2. Start backend server: `cd backend && npm start`
3. Access frontend at: `http://localhost:3000`
4. Test both code and idea modes with different iteration counts

### Configuration Options

- **Iterations**: 1-10 rounds (default: 3)
- **Code Analysis**: Configurable root path (default: current directory)
- **Output Prefix**: Custom filename prefixes for organization
- **File Extensions**: Easily extendable in `codeAnalyzer.js:4`

### Error Handling

The system implements comprehensive error handling:
- CLI command validation and execution errors
- File system access permissions
- API request/response validation
- Graceful degradation for missing or unreadable files

## Potential Extensions

The architecture supports several enhancement areas:
- Task queuing and progress tracking
- Multiple model support and parameter tuning
- Advanced mermaid diagram rendering
- Patent template customization
- Integration with patent office APIs