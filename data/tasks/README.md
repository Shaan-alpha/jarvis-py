# data/tasks/

Reminder persistence lives here as `tasks.json`. Gitignored — your
reminders are private.

## How it gets populated

Say:

> "hey jarvis"  
> "remind me in 10 minutes to drink water"

`core/tasks/task_parser.py` regex-parses that into
`{"minutes": 10, "message": "drink water"}`, and `TaskManager` stores
the absolute trigger time in `tasks.json`.

A `threading.Timer` is scheduled in-process. Pending reminders are
restored from disk on the next startup, so a quick app restart inside
the reminder window won't lose them.
