# Useful Prompts for Claude AI

## Introduction

This document provides a collection of effective prompts for working with Claude AI in software development contexts. Use these prompts as starting points and adapt them to your specific needs. 

These prompts assume, you have a project set up with good context in Claude AI.

## Context Assessment

Use these prompts to evaluate and refine the context that Claude has available:

### Explain what is in the Context
```
Explain what the code in the context does.
```
**Purpose**: Verifies Claude's understanding of your codebase. Use this as a first step to confirm Claude correctly interprets the code structure and purpose.

**Expected output**: A high-level overview of the main components in the context, their relationships, and primary functionality.

### Missing Context
```
If you are missing a class that you think is necessary, please tell me. 

If you make assumptions about the behavior of code that you don't see, please mention that as well.
```
**Purpose**: Identifies gaps in the provided context that might impact Claude's ability to give accurate responses.

**Expected output**: A list of classes, functions, or files that Claude believes are referenced but not included in the context, along with any assumptions it's making about their behavior.

**Tip**: Run this prompt before starting complex implementation tasks to avoid building on incomplete information.

---

## Implementation Planning

These prompts help with planning and structuring implementation work:

### Masterplan
```
Problem/Feature description...

Ask me questions that need to be answered before coming up with a master plan of how to implement this.
```
**Purpose**: Facilitates requirements gathering and elicitation through guided questioning.

**Expected output**: A series of clarifying questions about requirements, constraints, and implementation details, followed by a comprehensive implementation plan once you've provided answers.

**Tip**: Be thorough in your answers to Claude's questions, as the quality of the masterplan directly correlates to the completeness of the information provided. Check the generated specification thoroughly, probably you have to do some manual fixes. Then, check-in the specification and put it into the context

### Implement Masterplan
```
I want to implement what is described in `master-plan.md`. What are next steps in implementing the master plan? Give me a high-level overview first. (do not include detailled code)
```
**Purpose**: Breaks down a comprehensive plan into actionable steps, and implement them step-by-step.

**Expected output**: A high-level summary of implementation stages followed by more detailed next steps to begin the implementation process.

**Tip**: This only works if `master-plan.md` is included in your project context.

### Incremental Changes
```
Keep the existing code intact as much as possible, and only generate modified code.
```
**Purpose**: Ensures Claude recommends targeted changes rather than complete rewrites.

**Expected output**: Code suggestions that respect the existing codebase structure and only modify what's necessary.

**Tip**: Use this as a qualifier alongside other prompts when working with established codebases where minimizing changes is important.

### Check
```
I applied your proposals into the context. Did I apply it correctly?
```
**Purpose**: Validates that your implementation of Claude's suggestions matches its intent.

**Expected output**: Confirmation of correct application or identification of discrepancies or misunderstandings.

**Tip**: Run this after applying an increment proposed by the AI and after you push it into the context.

---

## Documentation and Summarization

These prompts help with documentation and managing long conversations:

### Summarize Chat
```
Generate a new prompt, that summarizes the conversation so far, and can be used as a new starting point.
```
**Purpose**: Condenses long conversations into a compact form for fresh starts or sharing.

**Expected output**: A comprehensive prompt that captures key points from your conversation, ready to use as a new conversation starter.

**Tip**: This might work if you end up in a long-winded chat and want to start fresh. Not always applicable.

### Architectural Description
```
Create an architectural description of the `xxx` package in a separate markdown file.
I am not interested in Key Design Patterns - unless there is a design pattern which play a major role.
```
**Purpose**: Generates documentation that explains the architecture of a specific component.

**Expected output**: A structured markdown document describing the architecture, components, interactions, and important design considerations.

