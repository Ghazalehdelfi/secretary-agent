# 🤖 Agents Directory

This directory contains all the Agent2Agent (A2A) implementations in the system. Each agent is a specialized AI assistant that can handle specific types of tasks and communicate with other agents through the A2A protocol.

## 📁 Directory Structure

```
agents/
├── host_agent/          # Orchestrator agent that routes requests to other agents
├── calendar_agent/      # Calendar management agent with Google Calendar integration
├── sync_agent/          # Synchronization agent for coordinating between services
└── README.md           # This file
```

## 🎯 Agent Overview

### Host Agent (`host_agent/`)
The **Orchestrator Agent** is the central coordinator that:
- Discovers and manages other A2A agents
- Routes user requests to appropriate child agents
- Uses Google's Agent Development Kit (ADK) with Gemini LLM
- Provides a unified interface for multi-agent interactions

**Key Features:**
- Agent discovery via registry
- Intelligent request routing
- Session management across agents
- Tool-based delegation to child agents

### Calendar Agent (`calendar_agent/`)
A specialized agent for calendar management that:
- Integrates with Google Calendar API
- Manages meeting scheduling and availability
- Handles contact lookup and email coordination
- Supports both real and mock modes for testing

**Key Features:**
- Check calendar availability
- Create and manage calendar events
- Contact integration via phonebook
- Email session management
- Timezone-aware scheduling

### Sync Agent (`sync_agent/`)
A synchronization agent that:
- Coordinates between different services
- Manages data consistency
- Handles cross-service communication
- Provides synchronization status and updates

**Key Features:**
- Service synchronization
- Data consistency management
- Status reporting
- Error handling and recovery

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Google API credentials (for calendar agent)
- Environment variables configured (see main README.md)

### Running Agents

Each agent can be started independently, but due to the dependencies they should be started in the below order:

```bash
# Start the calendar agent
python -m agents.calendar_agent --host localhost --port 10003

# Start the sync agent
python -m agents.sync_agent --host localhost --port 10004

# Start the host agent (orchestrator)
python -m agents.host_agent.entry --host localhost --port 10002

```

### Agent Communication

Agents communicate using the A2A JSON-RPC protocol:
- **Discovery**: Agents register themselves and discover others via `.well-known/agent.json`
- **Task Delegation**: Host agent routes requests to appropriate child agents
- **Response Handling**: Results are returned through the same protocol

## 🔧 Configuration

### Environment Variables
- `GOOGLE_API_KEY`: Required for Gemini LLM access
- `SERVICE_EMAIL`: Email service account for calendar operations
- `SERVICE_PASSWORD`: Email service password
- `service-creds`: Google Calendar service account credentials (JSON)

### Agent Registry
Agents are discovered through the registry system:
- Static registry files define agent URLs
- Dynamic discovery via HTTP endpoints
- Automatic health checking and failover

## 📚 Architecture

### Agent Pattern
Each agent follows a consistent pattern:
1. **Agent Class**: Core logic and LLM integration
2. **Task Manager**: Handles A2A protocol requests
3. **Entry Point**: CLI interface for starting the server
4. **Tools**: Specialized functions the agent can call

### Communication Flow
```
User Request → Host Agent → Route to Child Agent → Process → Return Response
```

## 🛠️ Development

### Adding New Agents
1. Create a new directory under `agents/`
2. Implement the required agent interface
3. Add task manager for A2A protocol handling
4. Create entry point for server startup
5. Register in agent registry

### Testing
- Use mock modes for development
- Test agent discovery and communication
- Verify task delegation and response handling

## 📖 Related Documentation
- [Main README](../README.md) - Project overview and setup
- [Server Documentation](../server/README.md) - A2A server implementation
- [Models Documentation](../models/README.md) - Data models and schemas
- [Utilities Documentation](../utilities/README.md) - Helper functions and services 