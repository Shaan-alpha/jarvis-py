# Jarvis Architecture

## Overview

Jarvis is a modular AI assistant system built with Python.

The project is designed to evolve from a simple voice assistant into a scalable offline-capable AI operating system inspired by Iron Man's JARVIS.

---

# Core Architecture

```text
Voice Input
    ↓
Speech Recognition
    ↓
Command Router
    ↓
Known Command?
   ↙        ↘
 YES         NO
 ↓            ↓
Execute      Local LLM
Command       ↓
         AI Response
               ↓
         Text To Speech