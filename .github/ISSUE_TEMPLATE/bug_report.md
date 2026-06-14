---
name: Bug report
about: Report incorrect or unexpected mcpbin behavior
title: "[bug] "
labels: bug
---

**What happened**
A clear description of the bug.

**Expected behavior**
What you expected instead.

**Reproduction**
Steps / the exact MCP call(s). Include the tool/resource/prompt name and arguments, e.g.:

```
tool: schema_enum
args: {"color": "purple"}
```

**Environment**
- mcpbin version / commit:
- How you run it: `uv run mcpbin --transport <stdio|sse|http>` / Docker / hosted Space
- Profile: `full` | `tools-only` | `no-sampling` | `minimal`
- MCP client (name + version):

**Logs / output**
Relevant stderr logs or the response/`_meta` you received (redact anything sensitive).
