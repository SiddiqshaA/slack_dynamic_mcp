# Slack MCP Server - Quick Guide

## Server URL
```
http://localhost:8000/sse
```

## Connect from Your Agent
```python
from mcp import ClientSession

async with ClientSession("http://localhost:8000/sse") as session:
    result = await session.call_tool(
        "tool_name",
        arguments={"user_id": "your_user_id", ...}
    )
```

## Available Tools

### User-Level (use xoxp- token from Supabase)
| Tool | Arguments | Returns |
|------|-----------|---------|
| `slack_get_user_profile` | `user_id` | User's profile |
| `slack_list_user_conversations` | `user_id`, `limit` | User's channels/DMs |
| `slack_fetch_conversation_history` | `user_id`, `channel_id`, `limit` | Messages |
| `slack_find_user_by_email` | `user_id`, `email` | User info |
| `slack_open_dm` | `user_id`, `slack_user_id` | DM channel ID |
| `slack_search_messages` | `user_id`, `channel_id`, `keyword`, `limit` | Matching messages |

### Bot-Level (use xoxb- token from .env)
| Tool | Arguments | Returns |
|------|-----------|---------|
| `slack_send_message` | `channel_id`, `text` | Message timestamp |
| `slack_standup` | `user_name`, `channel_id`, `standup_text` | Message timestamp |
| `slack_list_users` | - | All users |
| `slack_list_channels` | - | All channels |
| `slack_schedule_message` | `channel_id`, `text`, `post_at` | Scheduled message ID |
| `slack_create_channel` | `name`, `is_private` | Channel info |
| `slack_add_reaction` | `channel_id`, `timestamp`, `emoji` | Success status |

## Quick Example
```python
# Get user profile
profile = await session.call_tool(
    "slack_get_user_profile",
    arguments={"user_id": "krithika_123"}
)

# Send message
message = await session.call_tool(
    "slack_send_message",
    arguments={
        "channel_id": "C123456",
        "text": "Hello from agent!"
    }
)

# List channels
channels = await session.call_tool(
    "slack_list_channels",
    arguments={}
)
```

## Important
- **Always provide `user_id`** for user-level tools
- MCP server fetches user token from Supabase automatically
- All responses include `{"ok": true/false, ...data}`

