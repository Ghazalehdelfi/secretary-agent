# 🌐 Server Directory

This directory contains the core Agent2Agent (A2A) server implementation that handles communication between agents using the JSON-RPC 2.0 protocol over HTTP.

## 📁 Directory Structure

```
server/
├── server.py           # Main A2A server implementation
├── task_manager.py     # Task management and processing logic
└── README.md          # This file
```

## 🎯 Overview

The server module provides the foundation for A2A communication by implementing:
- **JSON-RPC 2.0 Protocol**: Standardized request/response format
- **HTTP Server**: Starlette-based ASGI web server
- **Task Management**: Abstract interface for processing agent tasks
- **Agent Discovery**: Metadata endpoint for agent identification

## 🔧 Core Components

### A2AServer (`server.py`)
The main server class that:
- Handles incoming HTTP requests
- Parses and validates JSON-RPC messages
- Routes tasks to appropriate task managers
- Provides agent discovery endpoints
- Manages error handling and response formatting

**Key Features:**
- Async request handling
- JSON-RPC 2.0 compliance
- Agent metadata exposure
- Comprehensive error handling
- Request/response logging

### TaskManager (`task_manager.py`)
Abstract interface and implementations for task processing:
- **TaskManager (ABC)**: Base interface defining required methods
- **InMemoryTaskManager**: Simple in-memory task storage
- **AgentTaskManager**: Integration with agent logic

**Key Features:**
- Abstract base class for consistency
- In-memory task storage
- Async task processing
- Session management
- Task history tracking

## 🚀 Usage

### Basic Server Setup

```python
from server.server import A2AServer
from server.task_manager import AgentTaskManager
from models.agent import AgentCard, AgentCapabilities

# Create agent metadata
agent_card = AgentCard(
    name="my_agent",
    description="A sample A2A agent",
    url="http://localhost:5000",
    version="1.0.0",
    capabilities=AgentCapabilities(),
    skills=[]
)

# Create task manager
task_manager = AgentTaskManager(your_agent)

# Create and start server
server = A2AServer(
    host="0.0.0.0",
    port=5000,
    agent_card=agent_card,
    task_manager=task_manager
)

server.start()
```

## 📡 API Endpoints

### POST `/`
Main endpoint for task requests:
- Accepts JSON-RPC 2.0 formatted requests
- Supports `send_task` and `get_task` methods
- Returns structured JSON-RPC responses

**Request Format:**
```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "method": "send_task",
  "params": {
    "id": "task-id",
    "sessionId": "session-id",
    "message": {
      "role": "user",
      "parts": [{"type": "text", "text": "Hello agent!"}]
    }
  }
}
```

### GET `/.well-known/agent.json`
Agent discovery endpoint:
- Returns agent metadata in standardized format
- Used by other agents for discovery and routing
- Contains capabilities, skills, and contact information

**Response Format:**
```json
{
  "name": "agent_name",
  "description": "Agent description",
  "url": "http://localhost:5000",
  "version": "1.0.0",
  "capabilities": {
    "streaming": false,
    "pushNotifications": false,
    "stateTransitionHistory": false
  },
  "skills": []
}
```

## 🔄 Task Lifecycle

1. **Task Submission**: Client sends task via POST `/`
2. **Validation**: Server validates JSON-RPC format and parameters
3. **Processing**: Task manager processes the request
4. **Response**: Server returns JSON-RPC response with results
5. **Status Tracking**: Task status can be queried via `get_task`

## 🛡️ Error Handling

The server implements comprehensive error handling:
- **JSON-RPC Errors**: Standard error codes and messages
- **HTTP Errors**: Proper status codes for different error types
- **Validation Errors**: Parameter and format validation
- **Processing Errors**: Task execution error handling

## 🔧 Configuration

### Environment Variables
- `HOST`: Server host address (default: "0.0.0.0")
- `PORT`: Server port number (default: 5000)
- `LOG_LEVEL`: Logging level (default: "INFO")

### Server Options
- **Host Binding**: Configure which interfaces to bind to
- **Port Selection**: Choose available port for the service
- **Agent Metadata**: Define agent capabilities and skills
- **Task Manager**: Select appropriate task processing logic
