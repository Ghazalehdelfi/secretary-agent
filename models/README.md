# 📊 Models Directory

This directory contains all the data models and schemas used throughout the Agent2Agent (A2A) system. These models define the structure of data exchanged between agents, clients, and servers using Pydantic for validation and serialization.

## 📁 Directory Structure

```
models/
├── agent.py           # Agent metadata and capabilities models
├── task.py            # Task lifecycle and message models
├── request.py         # JSON-RPC request/response models
├── json_rpc.py        # JSON-RPC 2.0 protocol models
└── README.md         # This file
```

## 🎯 Overview

The models module provides:
- **Data Validation**: Pydantic-based schema validation
- **Type Safety**: Strong typing for all data structures
- **Serialization**: JSON serialization/deserialization
- **Protocol Compliance**: A2A and JSON-RPC 2.0 compliance