# Lean 4 Automated Theorem Prover

**Author:** Justin Karbowski 
**Course:** Advanced Large Language Model Agents, Spring 2025
**Date:** May 30, 2025

## Overview

This project implements a sophisticated three-agent system for automated Lean 4 theorem proving, featuring strategic planning, code generation, and verification with retrieval-augmented generation (RAG).

## Architecture

- **Planning Agent (GPT-4o)**: Strategic task decomposition
- **Generation Agent (GPT-4o)**: Lean 4 code and proof synthesis  
- **Verification Agent (GPT-3.5-turbo)**: Error analysis and debugging

## Features

- Multi-agent coordination with iterative refinement
- RAG-enhanced generation using Lean 4 documentation
- Advanced error handling with learning from failures
- Robust Lean 4 compilation and verification

## Setup Instructions

# Install dependencies
   ```bash
   pip install -r requirements.txt

# Edit .env and add your OpenAI API key
   cp .env.example .env

## Usage

```bash
# Run single test
make test-single TASK=task_id_0

# Run all tests  
make test

# Package submission
make zip