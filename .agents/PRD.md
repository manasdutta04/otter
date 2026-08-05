# veridexs
> The AI Software Engineer for Modern Development Teams

![Status](https://img.shields.io/badge/status-planning-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

# Vision

veridexs is **not another AI chatbot**.

veridexs is an **AI Software Engineer** that deeply understands an entire codebase,
helps developers understand architecture,
plans implementations,
writes production-ready code,
reviews pull requests,
improves architecture,
and becomes the engineering memory of a project.

The goal is to build something that developers genuinely use every day.

Think:

- Cursor
- Devin
- OpenHands
- Sourcegraph
- CodeRabbit

—but focused on **engineering intelligence**, not just code generation.

---

# Problem

Current AI coding tools mainly generate code.

They usually do **not**:

- Understand an entire codebase
- Explain architecture
- Understand engineering decisions
- Track technical debt
- Suggest better system design
- Act like a senior engineer

veridexs fills this gap.

---

# Target Users

- Software Engineers
- AI Engineers
- Startup Teams
- CTOs
- Engineering Managers
- Open Source Maintainers
- Students learning large codebases

---

# Core Philosophy

veridexs should think like a **Senior Engineer**.

Not like ChatGPT.

It should:

✔ Understand

✔ Explain

✔ Plan

✔ Improve

✔ Build

✔ Review

✔ Learn

---

# Product Architecture

                     veridexs Platform

             ┌──────────────────────────┐
             │      Web Dashboard        │
             └────────────┬─────────────┘
                          │
      ┌───────────────────┼────────────────────┐
      │                   │                    │
      ▼                   ▼                    ▼
 veridexs API       veridexs CLI       VSCode Extension

                          │
                          ▼

                 Agent Orchestration
                 (LangGraph)

                          │

        ┌──────────────────────────────────┐
        │                                  │
        ▼                                  ▼

 Repository Intelligence          AI Coding Engine

        │                                  │

        ▼                                  ▼

 Vector Database                 GitHub Integration

        │                                  │

        ▼                                  ▼

 PostgreSQL                     Redis / Queue

---

# Tech Stack

## Backend

- Python
- FastAPI
- SQLAlchemy
- PostgreSQL
- Redis
- Celery

---

## AI

- LangGraph
- LiteLLM
- OpenAI
- Claude
- Gemini
- Ollama
- MCP
- RAG
- Qdrant

---

## Frontend

- Next.js

- TypeScript

- TailwindCSS

- shadcn/ui

---

## DevOps

- Docker

- GitHub Actions

- AWS

- Nginx

---

# Core Features

---

## 1. Repository Intelligence

Upload a GitHub repository.

veridexs automatically generates:

- Project Summary
- Folder Explanation
- Tech Stack
- API Flow
- Database Relationships
- Entry Points
- Dependency Graph
- Architecture Diagram

Example:

User:

"Explain this repository."

veridexs:

✔ Architecture

✔ Folder purpose

✔ Request lifecycle

✔ Authentication flow

✔ Database

✔ External APIs

---

## 2. Repository Chat

Examples

Where is authentication?

How does payment work?

Show JWT flow.

Explain middleware.

Where is caching implemented?

Find dead code.

Show duplicate logic.

Find performance bottlenecks.

---

## 3. Engineering Memory

veridexs remembers

- previous conversations

- architecture

- coding style

- project conventions

- team decisions

- naming patterns

No repeated explanations.

---

## 4. AI Planner

Example

User:

"Add Google OAuth"

veridexs

↓

Analyzes repository

↓

Finds required files

↓

Creates implementation plan

↓

Explains dependencies

↓

Estimates complexity

↓

Shows checklist

---

## 5. AI Coding

User requests feature.

veridexs

- finds files

- edits code

- generates tests

- explains changes

- creates commit

- creates PR

Human approval required before applying changes.

---

## 6. AI Code Review

Instead of saying

LGTM

veridexs checks

- Performance

- Security

- SQL

- Architecture

- Complexity

- Naming

- Error Handling

- Documentation

- Test Coverage

- API Design

---

## 7. Repository Health

Every repository receives

Architecture Score

Security Score

Maintainability Score

Performance Score

Technical Debt Score

Documentation Score

Dependency Health

Complexity Analysis

Dead Code Detection

Unused Dependencies

---

## 8. AI Architect

User

"I'm expecting 500k users."

veridexs suggests

- Caching

- Queues

- Load balancing

- Database optimization

- CDN

- Event-driven architecture

- Cost estimation

- Trade-offs

---

## 9. Engineering Dashboard

Dashboard includes

- Model Usage

- Prompt Cost

- API Usage

- Technical Debt

- Architecture

- PR Activity

- AI Suggestions

- Token Analytics

---

# Future Features

## VS Code Extension

Commands

Explain

Review

Generate Tests

Architect

Fix

Plan

Refactor

---

## GitHub App

Automatic PR reviews

Architecture suggestions

Performance comments

Security findings

Missing tests

Documentation review

---

## veridexs CLI

veridexs explain

veridexs review

veridexs architect

veridexs health

veridexs plan

veridexs analyze

veridexs docs

---

## MCP Server

Connect veridexs to

GitHub

Notion

Slack

Jira

Linear

Figma

Databases

Google Drive

---

# Folder Structure

veridexs/

    apps/
        web/
        api/
        cli/
        vscode/
        github-app/

    packages/
        agent/
        planner/
        analyzer/
        prompts/
        graph/
        memory/
        retrieval/
        github/
        architecture/
        review/
        health/
        shared/

    docs/

    examples/

    docker/

---

# Roadmap

## Phase 1

Repository Intelligence

Repository Chat

Authentication

GitHub Import

Basic Dashboard

---

## Phase 2

Planning Engine

Architecture Graph

Memory

Documentation Generator

---

## Phase 3

AI Coding

PR Generation

GitHub Integration

Testing

---

## Phase 4

Repository Health

Code Review

Architecture Analysis

Performance Analyzer

---

## Phase 5

VS Code Extension

CLI

GitHub App

MCP Server

---

# Design Principles

veridexs should

✅ Explain before coding

✅ Think before generating

✅ Show reasoning

✅ Respect project conventions

✅ Never overwrite code silently

✅ Ask for approval

---

# Long-Term Vision

veridexs becomes the operating system for software engineering.

Instead of opening multiple tools:

- GitHub
- ChatGPT
- Cursor
- Notion
- Jira
- Documentation

Developers interact with veridexs.

veridexs becomes the engineering brain of every project.

---

# Success Criteria

veridexs is successful when a developer says:

"I understand this repository in 10 minutes."

instead of

"I need two weeks to understand this codebase."

---

# Learning Goals (for the builder)

This project should help master:

- FastAPI
- LangGraph
- RAG
- MCP
- GitHub APIs
- Tree-sitter
- System Design
- Redis
- PostgreSQL
- Docker
- Background Workers
- AI Evaluation
- Prompt Engineering
- Code Analysis
- Software Architecture

---

# Non-Goals

veridexs is NOT:

- Another ChatGPT wrapper
- Another PDF chatbot
- Another AI search engine
- Another CRUD SaaS
- Another Cursor clone

veridexs is an engineering intelligence platform.

---

# Guiding Principle

Every feature must answer this question:

> "Would a senior software engineer actually use this every day?"

If the answer is **No**, don't build it.

If the answer is **Yes**, prioritize it.
