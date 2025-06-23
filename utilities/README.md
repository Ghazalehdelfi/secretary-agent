# 🛠️ Utilities Directory

This directory contains helper functions, services, and utilities that support the Agent2Agent (A2A) system. These utilities provide common functionality used across different agents and components.

## 📁 Directory Structure

```
utilities/
├── discovery.py        # Agent discovery and registry management
├── email_service.py    # Email sending and receiving functionality
├── email_session.py    # Email session management and tracking
├── phonebook.py        # Contact management and lookup
├── supabase_client.py  # Database client for Supabase integration
└── README.md          # This file
```

## 🎯 Overview

The utilities module provides:
- **Agent Discovery**: Finding and connecting to other A2A agents
- **Email Services**: Sending emails and managing email sessions
- **Contact Management**: Phonebook functionality for contact lookup
- **Database Integration**: Supabase client for data persistence
- **Session Management**: Tracking and managing communication sessions

## 🔧 Core Utilities

### Discovery (`discovery.py`)

#### DiscoveryClient
Manages agent discovery and registry operations:

**Features:**
- Async HTTP requests to agent endpoints
- Automatic error handling and logging
- Registry management
- Agent metadata parsing

### Email Service (`email_service.py`)

#### EmailService
Handles email operations using SMTP and IMAP:

**Features:**
- SMTP email sending
- IMAP email receiving
- Reply detection and processing
- Session-based email tracking
- Error handling and logging

### Email Session (`email_session.py`)

#### Session
Manages email communication sessions:

**Features:**
- Session creation and tracking
- Message history management
- Contact association
- Database persistence
- Session lookup by email

### Phonebook (`phonebook.py`)

#### Contact
Represents contact information

#### Phonebook
Manages contact lookup and storage

**Features:**
- Contact storage and retrieval
- Name-based lookup
- Email-based search
- Contact validation
- Database integration

### Supabase Client (`supabase_client.py`)

#### SupabaseClient
Database client for Supabase integration

**Features:**
- Async database operations
- Session data management
- Error handling
- Connection management
- Data validation
