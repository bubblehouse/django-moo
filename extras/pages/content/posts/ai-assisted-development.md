+++
date = '2026-03-27T00:00:00-04:00'
draft = false
title = 'AI-Assisted Development on DjangoMOO'
+++

For the last several months, DjangoMOO made heavy use of Claude Code, Anthropic's AI coding assistant. This post is a record of what that looked like and what it produced.

The first substantive use was unit test generation. The verbs themselves were mostly human-written, but generating tests for them turned out to be the fastest way to surface problems. The tests exposed incorrect output routing, dispatch edge cases where the wrong object ended up as `this`, and a handful of bugs in the underlying parser logic. Over several sessions, the discoveries from that process accumulated into a shared knowledge base that the next session could read rather than rediscover.

The security audit was the most intensive use of AI. The sandbox is the engineering core of the project. If a player can escape it, they own the server. Over seventeen passes, we worked through every category of Python sandbox escape: attribute access, module imports, code object injection, class hierarchy traversal. Each pass added tests and patched the vector it found. The final count was fifty holes sealed and 130 tests written, which are now a regression suite.

Around the same time, the project built a layer of specialized Claude Code skill files — structured prompts that load domain knowledge into an AI session before it starts work: `verb-author` for the parser reference and sandbox gotcha list, `game-designer` for building multi-room environments from a YAML spec, `sandbox-auditor` for security passes, and `tech-librarian` for keeping the Sphinx documentation in sync with the implementation. Combined with a persistent memory system that carries notes across sessions, each new AI session starts with months of accumulated project context rather than a blank slate.

The later work shifted toward infrastructure. The SSH output parsing pipeline was built entirely by the AI: PREFIX/SUFFIX delimiters to bracket command output, a `TERM=moo-automation` override to disable Cursor Position Report sequences, and a quiet mode that strips Rich color codes. The speed improvement made two things practical that weren't before: stress-testing the client SSH connection under load, and automating the build of complex MOO environments from YAML specs. Several other infrastructure issues got traced the same way:

- The asyncssh text editor was overwriting characters at column-80 boundaries because the library's built-in line editor was doing a second pass over prompt_toolkit output. The fix was a single flag: `line_editor=False`.
- The WebSSH ingress had an IP mismatch on Kubernetes because `externalTrafficPolicy: Cluster` caused kube-proxy SNAT, making the client IP inconsistent between the POST and WebSocket legs of the connection.

AI changed the pace of development without changing what was being built. The security audit happened faster and more thoroughly than it would have otherwise. The accumulated reference knowledge got written down in a structured form that an AI session can read at the start of a conversation, rather than scattered across notes or recreated from scratch each time.
