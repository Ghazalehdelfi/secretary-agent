# 🎯 Host Agent Directory

This directory contains the **Orchestrator Agent** implementation, which serves as the central coordinator for the A2A system. The host agent discovers other agents, routes user requests to appropriate child agents, and manages the overall communication flow.

## 📁 Directory Structure

```
host_agent/
├── entry.py           # CLI entry point for starting the orchestrator server
├── orchestrator.py    # Core orchestrator agent with LLM-based routing
├── agent_connect.py   # Agent connector for A2A communication
└── README.md         # This file
```

## 🎯 Overview

The Host Agent (Orchestrator) is the central nervous system of the A2A network that:
- **Discovers Agents**: Automatically finds and connects to other A2A agents
- **Routes Requests**: Uses LLM intelligence to determine which agent should handle each request
- **Manages Sessions**: Maintains conversation context across agent interactions
- **Coordinates Communication**: Handles the flow of information between agents

## 🔧 Core Components

### OrchestratorAgent (`orchestrator.py`)

The main orchestrator class that uses Google's Agent Development Kit (ADK) with Gemini LLM:

```python
class OrchestratorAgent:
    """
    🤖 Uses a Gemini LLM to route incoming user queries,
    calling out to any discovered child A2A agents via tools.
    """
```

**Key Features:**
- **LLM-Based Routing**: Uses Gemini to intelligently route requests
- **Agent Discovery**: Automatically discovers available child agents
- **Tool-Based Delegation**: Calls child agents through function tools
- **Session Management**: Maintains conversation context across calls
- **Error Handling**: Graceful handling of agent failures

**Available Tools:**
1. `list_agents()` → Returns list of available child agents
2. `delegate_task(agent_name, message)` → Sends task to specific agent

### OrchestratorTaskManager (`orchestrator.py`)

A2A protocol adapter that exposes the orchestrator via JSON-RPC:

```python
class OrchestratorTaskManager(InMemoryTaskManager):
    """
    🪄 TaskManager wrapper: exposes OrchestratorAgent.invoke() over the
    A2A JSON-RPC `tasks/send` endpoint, handling in-memory storage and
    response formatting.
    """
```

**Responsibilities:**
- Handles incoming A2A task requests
- Delegates processing to OrchestratorAgent
- Manages task lifecycle and history
- Returns structured JSON-RPC responses

### AgentConnector (`agent_connect.py`)

Lightweight wrapper for communicating with child A2A agents:

```python
class AgentConnector:
    """
    🔗 Lightweight wrapper around A2AClient to call other agents.
    """
```

**Features:**
- Simplified interface for agent communication
- Automatic session management
- Error handling and retry logic
- Response parsing and validation

### Entry Point (`entry.py`)

CLI interface for starting the orchestrator server:

```python
# Start the orchestrator agent server
python -m agents.host_agent.entry --host localhost --port 10002
```

## 🚀 Usage Examples

### Starting the Orchestrator

```bash
# Basic startup
python -m agents.host_agent.entry --host localhost --port 10002

# With custom configuration
python -m agents.host_agent.entry \
  --host 0.0.0.0 \
  --port 8080 \
  --registry http://localhost:10001,http://localhost:10003
```

### Agent Discovery

The orchestrator automatically discovers agents through:

1. **Registry URLs**: Provided at startup via `--registry` parameter
2. **Agent Cards**: Fetched from each agent's `/.well-known/agent.json` endpoint
3. **Dynamic Addition**: Agents can be added during runtime

### Request Routing

The orchestrator uses LLM intelligence to route requests:

```python
# Example: User asks "What time is it?"
# Orchestrator determines this should go to the time agent
# Delegates to time agent and returns response

# Example: User asks "Schedule a meeting with John"
# Orchestrator determines this should go to the calendar agent
# Delegates to calendar agent and returns response
```

## 🔄 Communication Flow

```
User Request → Orchestrator Agent → LLM Analysis → Route to Child Agent → Response
```

1. **Request Reception**: A2A server receives JSON-RPC request
2. **Task Management**: OrchestratorTaskManager processes the request
3. **LLM Analysis**: OrchestratorAgent uses Gemini to analyze the request
4. **Agent Selection**: LLM determines which child agent should handle the request
5. **Delegation**: Request is sent to the selected child agent
6. **Response**: Child agent response is returned to the user

## 🛠️ Configuration

### Environment Variables

- `GOOGLE_API_KEY`: Required for Gemini LLM access
- `HOST`: Server host address (default: localhost)
- `PORT`: Server port number (default: 5000)

### Agent Registry

The orchestrator discovers agents through a registry system:

```bash
# Static registry (+separated URLs)
--registry http://localhost:10001+http://localhost:10003

# Dynamic discovery (agents register themselves)
# Agents can be added/removed during runtime
```

### LLM Configuration

The orchestrator uses Google's Gemini model:

```python
# Model configuration in orchestrator.py
return LlmAgent(
    model="gemini-2.5-flash",    # Gemini model version
    name="orchestrator_agent",   # Agent identifier
    description="Delegates user queries to child A2A agents based on intent.",
    instruction=system_instr,    # System instructions
    tools=[...]                  # Available tools
)
```