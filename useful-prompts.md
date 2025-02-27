# Useful Prompts for Claude AI

## Introduction

This document provides a collection of effective prompts for working with Claude AI in software development contexts. Use these prompts as starting points and adapt them to your specific needs. 

These prompts assume, you have a project set up with good context in Claude AI.

### Explain what is in the Context
```
Explain what the code in the context does.
```
Good starting point to figure out if the AI understands what is provided in the project

### Missing Context
```
If you are missing a class that you think is necessary, please tell me. 

If you make assumptions about the behavior of code that you don't see, please mention that as well.
```
Let the AI tell you what might be missing in the context.

---

### Masterplan
```
Problem/Feature description...

Ask me questions that need to be answered before coming up with a master plan of how to implement this.
```
Let the AI ask you questions about how to implement a particular feature. Then the AI generates a specification. Check the generated specification thoroughly, probably you have to do some manual fixes. Then, check-in the specification and put it into the context

### Implement Masterplan
```
I want to implement what is described in `master-plan.md`. What are next steps in implementing the master plan? Give me a high-level overview first.
```
Ideally, this works idempotently.

### Incremental Changes
```
Keep the existing code intact as much as possible, and only generate modified code.
```
General advice.

### Check
```
I applied your proposals into the context. Did I apply it correctly?
```
Run this after applying an increment proposed by the AI and after you push it into the context.

---

### Summarize Chat
```
Generate a new prompt, that summarizes the conversation so far, and can be used as a new starting point.
```
This might work if you end up in a long-winded chat and want to start fresh. Not always applicable.

### Architectural Description
```
Create an architectural description of the `xxx` package in a separate markdown file.
I am not interested in Key Design Patterns - unless there is a design pattern which play a major role.
```

### Text Continuation
```
Continue this text:
...

It should go in this direction:
...
```

