---
name: processkiller
description: >
  Identify and terminate processes by port number, process name, or PID.
  Cross-platform (Windows, macOS, Linux). Use when the user asks to kill
  a process by port, name, or PID, or mentions port conflicts, occupied
  ports, stuck processes, or wants to free up a port. Also triggers on
  phrases like "kill process", "占用端口", "结束进程", "释放端口",
  "force close", "terminate process".
license: MIT
---

# ProcessKiller

Identify the process occupying a given port, or find a process by name or PID,
then ask the user for confirmation before terminating it.

## Workflow

```
User provides input
        │
        ▼
┌──────────────────────┐
│ Step 1: Identify     │ ← Determine input type: port, process name, or PID
│         input type   │
└──────────────────────┘
        │
        ▼
┌──────────────────────┐
│ Step 2: Find process │ ← Run OS-specific commands to locate the process
└──────────────────────┘
        │
        ▼
┌──────────────────────┐
│ Step 3: Show details │ ← Display process name, PID, port (if applicable)
└──────────────────────┘
        │
        ▼
┌──────────────────────┐
│ Step 4: AskUser      │ ← Ask user: "Kill this process?"
└──────────────────────┘
        │
     ┌──┴──┐
     ▼     ▼
   Yes    No
   kill  done
```

## Step 1: Identify Input Type

Determine what the user provided:

- **Port number**: A number between 1-65535 (e.g., `3000`, `8080`)
- **Process name**: A string that looks like an executable name (e.g., `node.exe`, `python`, `java`)
- **PID**: A positive integer, typically 4-6 digits (e.g., `1234`, `5678`)

If ambiguous (e.g., `8080` could be a port or a PID), default to treating it as a port number. If the user explicitly says "PID 8080" or "process 8080", use that context.

## Step 2: Find Process

### By Port Number

**Windows:**
```bash
netstat -ano | findstr /R "^[^:]*:[0-9]*:.*<PORT> "
```

Or using PowerShell:
```powershell
Get-NetTCPConnection -LocalPort <PORT> | Select-Object -ExpandProperty OwningProcess
```

**macOS / Linux:**
```bash
lsof -i :<PORT> -t 2>/dev/null
```
Or:
```bash
ss -tlnp "sport = :<PORT>" | grep -oP 'pid=\K[0-9]+'
```

### By Process Name

**Windows:**
```bash
tasklist /FI "IMAGENAME eq <NAME>" /FO CSV /NH
```
Or:
```bash
wmic process where "name='<NAME>'" get ProcessId,Name,CommandLine /format:list
```

**macOS / Linux:**
```bash
pgrep -a <NAME>
```
Or:
```bash
ps aux | grep -i <NAME> | grep -v grep
```

### By PID

**All platforms:**
```bash
# Windows
tasklist /FI "PID eq <PID>" /FO CSV /NH

# macOS / Linux
ps -p <PID> -o pid,comm,args
```

## Step 3: Display Results

Show the user a clear summary:

```
Found process(es):
┌──────┬──────────────┬─────────┬──────────────────────────────┐
│ PID  │ Name         │ Port(s) │ Command Line                 │
├──────┼──────────────┼─────────┼──────────────────────────────┤
│ 1234 │ node.exe     │ 3000    │ node server.js               │
└──────┴──────────────┴─────────┴──────────────────────────────┘
```

If multiple processes match, show all of them and let the user decide which to kill (or kill all).

If no process is found, tell the user clearly and suggest alternatives.

## Step 4: Ask for Confirmation

Use the **AskUserQuestion** tool to ask:

- **Question**: "是否结束该进程？" / "Kill this process?"
- **Options**: ["是，结束进程", "否，取消操作"]
- **Header**: "确认操作"

If multiple processes are found, ask:
- **Options**: ["全部结束", "只结束指定进程", "取消操作"]

## Step 5: Terminate (Only if User Confirms)

**Windows:**
```bash
taskkill /PID <PID> /F
```

**macOS / Linux:**
```bash
kill -9 <PID>
```

Report the result back to the user:
- If successful: "进程 <PID> (<name>) 已成功结束"
- If failed: "无法结束进程 <PID>: <error>" and suggest running as administrator / using sudo.

## Edge Cases

### No process found
- Inform the user clearly: "未找到占用端口 <PORT> 的进程" or "未找到名为 <NAME> 的进程"
- Suggest checking if the service is running, or verifying the port/name

### Multiple processes found
- Show all matches with full details
- Let user choose which to kill, or kill all

### Permission denied
- On Windows: suggest "以管理员身份运行"
- On macOS/Linux: suggest using `sudo`

### System-critical processes
- Warn the user if the process appears to be a system process (e.g., `svchost.exe`, `system`, `launchd`)
- Ask for explicit confirmation: "这是一个系统进程，结束它可能导致系统不稳定。确定要继续吗？"

### Input validation
- Port must be 1-65535
- PID must be a positive integer
- Process name must be non-empty and reasonable (< 256 chars)
- Reject obviously invalid input before running commands
