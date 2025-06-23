# 🎯🚀 Secretary Agent, the future of communication prototype with A2A and ADK
This project demonstrates how to build, serve, and interact with multiple A2A agents:
1. **OrchestratorAgent** – Central coordinator that routes requests to appropriate child agents
2. **CalendarAgent** – Manages Google Calendar operations and meeting scheduling
3. **SyncAgent** – Coordinates meeting scheduling between users
4. **Host Agent** – Orchestrates communication between all agents

All agents work together seamlessly via A2A discovery and JSON-RPC protocol.

---

## 📦 Project Structure

```bash
a2a_samples/
├── .env                         # Your GOOGLE_API_KEY (not committed)
├── pyproject.toml              # Dependency configuration
├── README.md                   # You are reading it!
├── agents/                     # All A2A agent implementations
│   ├── README.md              # Agents documentation
│   ├── host_agent/            # Orchestrator agent
│   │   ├── README.md          # Host agent documentation
│   │   ├── entry.py           # CLI entry point
│   │   ├── orchestrator.py    # Core orchestrator logic
│   │   └── agent_connect.py   # Agent communication wrapper
│   ├── calendar_agent/        # Calendar management agent
│   │   ├── __main__.py        # Server startup
│   │   └── agent.py           # Google Calendar integration
│   └── sync_agent/            # Meeting coordination agent
│       ├── __main__.py        # Server startup
│       ├── agent.py           # Sync logic
│       └── task_manager.py    # Task management
├── server/                     # A2A server implementation
│   ├── README.md              # Server documentation
│   ├── server.py              # JSON-RPC server
│   └── task_manager.py        # Task management interface
├── models/                     # Data models and schemas
│   ├── README.md              # Models documentation
│   ├── agent.py               # Agent metadata models
│   ├── task.py                # Task lifecycle models
│   ├── request.py             # JSON-RPC request models
│   └── json_rpc.py            # JSON-RPC protocol models
├── utilities/                  # Helper functions and services
│   ├── README.md              # Utilities documentation
│   ├── discovery.py           # Agent discovery
│   ├── email_service.py       # Email operations
│   ├── email_session.py       # Session management
│   ├── phonebook.py           # Contact management
│   └── supabase_client.py     # Database integration
├── client/                     # A2A client implementation
│   ├── README.md              # Client documentation
│   └── client.py              # JSON-RPC client
└── Dockerfiles/                # Container configurations
    ├── Dockerfile.host-agent
    ├── Dockerfile.calendar-agent
    └── Dockerfile.sync-agent
```

---

## 🛠️ Setup

1. **Clone & navigate**

    ```bash
    git clone https://github.com/theailanguage/a2a_samples.git
    cd a2a_samples
    ```

2. **Create & activate a venv**

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3. **Install dependencies**

    Using [`uv`](https://github.com/astral-sh/uv):

    ```bash
    uv pip install .
    ```

    Or with pip directly:

    ```bash
    pip install .
    ```

4. **Set your API key**

    Create `.env` at the project root:
    ```bash
    echo "GOOGLE_API_KEY=your_api_key_here" > .env
    ```

5. **Configure additional services** (optional)

    For full functionality, you may also need:
    - Google Calendar service account credentials
    - Email service credentials (SMTP/IMAP)
    - Supabase database credentials

---

## 🎬 Demo Walkthrough

**Start the Calendar Agent**
```bash
python3 -m agents.calendar_agent \
  --host localhost --port 10001
```

**Start the Sync Agent**
```bash
python3 -m agents.sync_agent \
  --host localhost --port 10002
```

**Start the Orchestrator (Host) Agent**
```bash
python3 -m agents.host_agent.entry \
  --host localhost --port 10003 \
  --registry http://localhost:10001,http://localhost:10002
```

**Try it out!**
Post your queries to the host agent's URL and you can communicate with the agent!
---

## 🔍 How It Works

### Agent Discovery & Communication
1. **Discovery**: OrchestratorAgent reads registry URLs, fetches each agent's `/.well-known/agent.json`
2. **Routing**: Based on intent, the Orchestrator's LLM calls its tools:
   - `list_agents()` → lists child-agent names
   - `delegate_task(agent_name, message)` → forwards tasks
3. **Child Agents**:
   - CalendarAgent manages Google Calendar operations
   - SyncAgent coordinates meeting scheduling between users
4. **JSON-RPC**: All communication uses A2A JSON-RPC 2.0 over HTTP

### Calendar Integration
- **Availability Checking**: CalendarAgent checks free time slots
- **Event Creation**: Creates calendar events with contact integration
- **Conflict Detection**: Prevents double-booking
- **Timezone Support**: Handles timezone-aware scheduling

### Meeting Coordination
- **Contact Management**: Phonebook integration for contact lookup
- **Email Communication**: Sends meeting requests to non-agent contacts
- **Session Tracking**: Maintains conversation history
- **Follow-up Management**: Handles email replies and updates

---

## 📚 Documentation

This project includes comprehensive documentation:

### 📖 README Files
- **[Main README](README.md)** - Project overview and setup (this file)
- **[Agents README](agents/README.md)** - All agent implementations
- **[Host Agent README](agents/host_agent/README.md)** - Orchestrator documentation
- **[Server README](server/README.md)** - A2A server implementation
- **[Models README](models/README.md)** - Data models and schemas
- **[Utilities README](utilities/README.md)** - Helper functions and services
- **[Client README](client/README.md)** - A2A client implementation

### 🔧 Code Documentation
- **Comprehensive Docstrings**: All classes and methods are fully documented
- **Inline Comments**: Detailed explanations throughout the codebase
- **Type Hints**: Full type annotations for better IDE support
- **Error Handling**: Comprehensive error handling with detailed messages

### 🎯 Key Features Documented
- **Agent Architecture**: How agents communicate and coordinate
- **Protocol Implementation**: JSON-RPC 2.0 over HTTP details
- **LLM Integration**: Google ADK and Gemini usage patterns
- **Database Integration**: Supabase client and data models
- **Email Services**: SMTP/IMAP operations and session management
- **Calendar Operations**: Google Calendar API integration
- **Contact Management**: Phonebook and lookup functionality

---

## 🚀 Advanced Features

### Multi-Agent Coordination
- **Intelligent Routing**: LLM-based request routing to appropriate agents
- **Session Management**: Conversation context across multiple agents
- **Error Recovery**: Graceful handling of agent failures
- **Dynamic Discovery**: Runtime agent registration and discovery

### Calendar Management
- **Real-time Availability**: Check calendar availability for any date
- **Smart Scheduling**: Conflict detection and resolution
- **Contact Integration**: Automatic contact lookup and invitation
- **Timezone Support**: Proper timezone handling for global teams

### Email Integration
- **Meeting Requests**: Send formatted meeting request emails
- **Reply Processing**: Automatic email reply detection and processing
- **Session Tracking**: Maintain conversation history for follow-ups
- **Contact Association**: Link emails to existing contacts

### Database Persistence
- **Contact Storage**: Persistent contact management
- **Session History**: Track all agent interactions
- **Email Sessions**: Store email conversation history
- **Scalable Architecture**: Supabase integration for cloud deployment

---

## 🔧 Configuration

### Environment Variables
```bash
# Required
GOOGLE_API_KEY=your_gemini_api_key

# Optional (for full functionality)
SERVICE_EMAIL=your_email@gmail.com
SERVICE_PASSWORD=your_app_password
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
service-creds={"type": "service_account", ...}
```

### Agent Configuration
Each agent can be configured independently:
- **Host Binding**: Configure which interfaces to bind to
- **Port Selection**: Choose available ports for each service
- **Registry Management**: Define agent discovery URLs
- **LLM Settings**: Configure model parameters and tools
