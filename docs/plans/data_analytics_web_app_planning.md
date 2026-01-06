# Data Analytics Web Application
## Comprehensive Planning Document

---

## Project Overview

This project aims to create a web-based interface for an existing Claude Code data analytics system that queries Matomo and Metabase data. The web application will provide both interactive chat functionality and persistent report management capabilities.

### Current State

- Existing Claude Code setup that successfully queries Matomo and Metabase
- Agent can generate reports and create visualizations
- System works well in terminal but lacks web interface
- Agent can modify its own documentation and skills
- Changes tracked via journal file and Git version control

### Desired State

- Web-based chat interface for interactive data exploration
- Reports dashboard for consolidated and persistent analyses
- Visual chart and graph generation capability in web browser
- Knowledge management interface for domain experts
- Google Workspace single sign-on for organization members
- Audit trail and version control for agent modifications

---

## User Interface

You can base your work on ~/Development/gip/autoplatformer, branch claude/redesign-menu-sections-YFY6C.
Use the same font, theme, general architecture.
The app is going to feature 2 sections for now (in its sidebar):

- Explorations et rapports (launching queries and creating reports)
- Connaissances (explore and edit context and knowledge)

Both have a sub-hierarchy (a list of documents on their main page). For Explorations, it's
the user's previous chats or compiled reports. For Connaissances, it's the documents in
./knowledge and ./skills.

When a document is open, there's a chat bar at the bottom, to edit / converse with said
document. In Explorations, the chat bar is always present, even on the main screen of the
section, so as to start a new chat.

## Technical Architecture

### Technology Stack

| Component | Technology |
|-----------|------------|
| Frontend Framework | Flask + HTMX + HTML/CSS/JavaScript |
| Backend Framework | Claude Agent SDK (Python) |
| Database | SQLite (for Metabase metadata and application data) |
| Skills Storage | Filesystem (.claude/skills/) with Git version control |
| Authentication | Google Workspace OAuth 2.0 SSO |
| Data Sources | Matomo Analytics + Metabase Business Intelligence |

### System Architecture

The application follows a hybrid architecture that combines web technologies with filesystem-based agent management.

#### Frontend Layer

- Flask web server serving HTML templates
- HTMX for real-time interactivity without complex JavaScript
- Streaming chat interface for interactive data queries
- Reports dashboard for saved and scheduled analyses
- Knowledge management interface for domain experts

#### Backend Layer

- Claude Agent SDK managing the agent lifecycle
- Existing Matomo and Metabase query logic
- Chart and visualization generation capabilities
- Session management and context preservation

#### Storage Layer

- SQLite database for Metabase cards, dashboards, and metadata
- Filesystem storage for Agent Skills (.claude/skills/)
- Git repository for version control of agent modifications
- Auto-commit mechanism for agent self-modification

---

## Application Features

### Chat Interface

Interactive conversational interface for data exploration and analysis:

- Real-time streaming responses using HTMX
- Natural language queries about Matomo and Metabase data
- Dynamic chart and graph generation in browser
- Session persistence for context across queries
- Ability to save interesting analyses to reports dashboard

### Reports Dashboard

Consolidated view of saved analyses and scheduled reports:

- List view of all saved reports with metadata
- Ability to request updates to existing reports
- Export capabilities for reports and visualizations
- Search and filtering functionality

### Knowledge Management

Separate interface for domain experts to maintain agent knowledge:

- Agent skill and prompt modification interface
- Database schema and query documentation management
- Agent self-modification capabilities with human oversight
- Audit trail of all modifications

---

## Authentication & Security

### Google Workspace Single Sign-On

Organization-restricted authentication using Google OAuth 2.0:

- OAuth app configured in Google Workspace admin console
- Domain verification to restrict access to organization members
- Session management for authenticated users
- Role-based access (regular users vs domain experts)

### Security Considerations

- Agent skill modifications require domain expert permissions
- All agent modifications logged with timestamps and user IDs
- Git version control provides rollback capabilities
- Sensitive data access controlled through existing Matomo/Metabase permissions

---

## Development Plan

### Phase 1: Basic Web Interface (MVP)

**Goal:** Create minimal viable web interface with chat functionality

1. Set up Flask application with HTMX
2. Integrate Claude Agent SDK backend
3. Implement basic chat interface with streaming responses
4. Connect to existing Matomo/Metabase query logic
5. Basic chart rendering in web browser

### Phase 2: Authentication & Data Persistence

**Goal:** Add user authentication and persistent data storage

1. Implement Google Workspace OAuth 2.0
2. Set up SQLite database schema
3. Migrate Metabase metadata to SQLite
4. Implement session management
5. Basic user permissions framework

### Phase 3: Reports Dashboard

**Goal:** Create persistent reports management interface

1. Design reports database schema
2. Build reports listing and detail views
3. Implement save-to-reports functionality from chat
4. Add report update and refresh capabilities
5. Export functionality for reports

### Phase 4: Knowledge Management

**Goal:** Enable domain experts to manage agent knowledge

1. Create knowledge management interface
2. Implement agent skill modification capabilities
3. Set up auto-commit to Git for agent changes
4. Add audit trail and change log functionality
5. Domain expert permission controls

### Phase 5: Polish & Deployment

**Goal:** Production-ready application with full feature set

1. UI/UX improvements and responsive design
2. Performance optimization
3. Error handling and user feedback
4. Testing and quality assurance
5. Deployment strategy and documentation

---

## Technical Requirements

### Performance Requirements

- Real-time streaming responses for chat interface
- Sub-second response time for simple queries
- Concurrent user support (initially 5-10 users)
- Efficient chart rendering and display

### Scalability Requirements

- SQLite sufficient for initial deployment
- Architecture allows future migration to PostgreSQL
- Filesystem skills storage scales with Git repository
- Session management supports increasing user base

### Compatibility Requirements

- Modern web browsers (Chrome, Firefox, Safari, Edge)
- Responsive design for desktop and tablet use
- Python 3.8+ for Claude Agent SDK compatibility
- Existing Matomo and Metabase API compatibility

---

## Data Storage Strategy

### SQLite Database Schema

```sql
-- Users table for session management
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user', -- 'user' or 'domain_expert'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Reports table for persistent analyses
CREATE TABLE reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    query_data TEXT, -- JSON containing query parameters
    chart_config TEXT, -- JSON containing chart configuration
    results_cache TEXT, -- Cached results for quick display
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Metabase metadata (migrated from existing system)
CREATE TABLE metabase_cards (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    query_text TEXT NOT NULL,
    database_name VARCHAR(100),
    table_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Chat sessions for context management
CREATE TABLE chat_sessions (
    id TEXT PRIMARY KEY, -- UUID
    user_id INTEGER NOT NULL,
    context_data TEXT, -- JSON containing conversation context
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Agent modification audit trail
CREATE TABLE agent_modifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    modification_type VARCHAR(50), -- 'skill_creation', 'skill_modification', 'prompt_update'
    file_path VARCHAR(500),
    change_summary TEXT,
    git_commit_hash VARCHAR(40),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### Filesystem Structure

```
project_root/
├── app/
│   ├── __init__.py
│   ├── main.py              # Flask application
│   ├── auth.py              # Google OAuth handling
│   ├── agent_interface.py   # Claude Agent SDK integration
│   ├── models.py            # Database models
│   └── templates/
│       ├── base.html
│       ├── chat.html
│       ├── reports.html
│       └── knowledge.html
├── .claude/
│   ├── skills/              # Agent skills (filesystem required)
│   │   ├── data_analysis/
│   │   ├── chart_generation/
│   │   └── metabase_queries/
│   └── CLAUDE.md           # Project context
├── data/
│   └── app.db              # SQLite database
├── static/
│   ├── css/
│   ├── js/
│   └── charts/             # Generated chart files
└── requirements.txt
```

---

## API Design

### Flask Routes

```python
# Authentication
GET  /                      # Landing page (redirect if authenticated)
GET  /login                 # Google OAuth login
GET  /auth/callback         # OAuth callback
POST /logout                # Logout user

# Chat Interface
GET  /chat                  # Chat interface page
POST /chat/message          # Send message to agent (HTMX)
GET  /chat/stream/<session> # Stream agent responses (SSE)

# Reports Dashboard
GET  /reports               # Reports listing page
GET  /reports/<id>          # Individual report view
POST /reports/save          # Save chat conversation as report
PUT  /reports/<id>/refresh  # Refresh report data
DELETE /reports/<id>        # Delete report

# Knowledge Management (domain experts only)
GET  /knowledge             # Knowledge management interface
GET  /knowledge/skills      # List agent skills
POST /knowledge/skills      # Create/modify skills
GET  /knowledge/audit       # Modification audit trail
```

### Agent Integration Points

```python
# Claude Agent SDK integration
from claude_agent_sdk import query, ClaudeAgentOptions

async def chat_with_agent(user_message, session_id, user_context):
    options = ClaudeAgentOptions(
        setting_sources=["project"],  # Load skills from filesystem
        allowed_tools=["Skill", "Read", "Write", "Bash", "Web"],
        session_id=session_id
    )
    
    async for message in query(
        prompt=user_message,
        options=options
    ):
        yield message  # Stream to frontend via HTMX
```

---

## Next Steps

### Immediate Actions

1. Set up development environment with Flask and Claude Agent SDK
2. Create project repository and basic directory structure
3. Design initial database schema for application data
4. Configure Google Workspace OAuth application
5. Begin Phase 1 development with basic web interface

### Success Criteria

The project will be considered successful when:

- Users can interact with data through web chat interface
- Charts and visualizations render correctly in browser
- Reports can be saved, managed, and updated
- Domain experts can modify agent knowledge safely
- All changes are audited and version controlled
- Authentication restricts access to organization members

---

## Implementation Notes for Claude Code

### Key Considerations

1. **Agent Skills Storage**: Must use filesystem (.claude/skills/) as required by Claude Agent SDK
2. **Hybrid Data Strategy**: SQLite for fast queries, filesystem for agent skills
3. **Auto-commit Workflow**: Agent modifications automatically committed to Git
4. **HTMX Streaming**: Use Server-Sent Events for real-time chat responses
5. **Session Management**: Preserve context across user interactions
6. **Domain Verification**: Check user email domain for organization access

### Flask + Claude Agent SDK Integration

The core integration pattern:

```python
# app/agent_interface.py
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions
from flask import current_app

class AgentInterface:
    def __init__(self):
        self.default_options = ClaudeAgentOptions(
            setting_sources=["project"],
            allowed_tools=["Skill", "Read", "Write", "Bash"]
        )
    
    async def process_message(self, message, session_id, user_id):
        # Load user context from database
        context = self.load_user_context(user_id)
        
        # Process with Claude Agent SDK
        async for response in query(
            prompt=f"{context}\n\nUser: {message}",
            options=self.default_options.with_session(session_id)
        ):
            yield response
            
        # Save updated context
        self.save_user_context(user_id, response.context)
```
