from fastmcp import FastMCP, Context
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

# Fallback tokens for local development/testing (optional)
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", None)
SLACK_USER_TOKEN = os.getenv("SLACK_USER_TOKEN", None)

# Supabase/FastAPI token service configuration
TOKEN_SERVICE_URL = os.getenv("TOKEN_SERVICE_URL", "https://leaseless-long-commutative.ngrok-free.dev")
TOKEN_SERVICE_API_KEY = os.getenv("TOKEN_SERVICE_API_KEY", "scrummaster123")

# MCP Server
mcp = FastMCP("Slack Automation MCP Server")

def get_token_from_service(user_id: str, provider: str = "slack") -> dict:
    """Fetch OAuth tokens from Supabase token service."""
    try:
        url = f"{TOKEN_SERVICE_URL}/get-token"
        params = {"provider": provider}
        if user_id:
            params["user_id"] = user_id
            
        headers = {"x-api-key": TOKEN_SERVICE_API_KEY}
        
        response = httpx.get(url, params=params, headers=headers, timeout=10.0)
        response.raise_for_status()
        
        data = response.json()
        
        if isinstance(data, list) and len(data) > 0:
            return data[0]
        return data
        
    except Exception as e:
        raise ValueError(f"Failed to fetch token from service: {e}")

def get_slack_client_from_context(ctx: Context, use_bot: bool = True, user_id: str = None) -> WebClient:
    """Get Slack client with token from Supabase, headers, or environment."""
    
    # Priority 1: For USER operations - Fetch from Supabase if user_id provided
    if not use_bot and user_id:
        try:
            token_data = get_token_from_service(user_id, "slack")
            token = token_data.get("access_token")
            
            if token and token.startswith("xoxp-"):
                print(f"✅ Using user token from Supabase (user_id: {user_id[:8]}...)")
                return WebClient(token=token)
            else:
                print(f"⚠️  No valid user token in Supabase for user_id: {user_id}")
                    
        except Exception as e:
            print(f"⚠️  Could not fetch token from Supabase: {e}")
            print(f"   Please provide user_id manually...")
            
            # Prompt for user_id from terminal
            try:
                manual_user_id = input("\n📝 Enter Supabase user_id (or press Enter to skip): ").strip()
                
                if manual_user_id:
                    print(f"   Attempting to fetch token for: {manual_user_id[:8]}...")
                    token_data = get_token_from_service(manual_user_id, "slack")
                    token = token_data.get("access_token")
                    
                    if token and token.startswith("xoxp-"):
                        print(f"✅ Using user token from Supabase (manual user_id)")
                        return WebClient(token=token)
                    else:
                        print(f"⚠️  No valid user token found for manual user_id")
                else:
                    print(f"   Skipping manual input, falling back to environment...")
                    
            except Exception as manual_error:
                print(f"⚠️  Manual fetch failed: {manual_error}")
                print(f"   Falling back to environment/header tokens...")
    
    # Priority 2: Try to get token from request headers
    if hasattr(ctx, 'request_context') and ctx.request_context:
        headers = ctx.request_context.get('headers', {})
        
        if use_bot:
            token = headers.get('x-slack-bot-token') or headers.get('X-Slack-Bot-Token')
            if token:
                return WebClient(token=token)
        else:
            token = headers.get('x-slack-user-token') or headers.get('X-Slack-User-Token')
            if token:
                return WebClient(token=token)
    
    # Priority 3: Fallback to environment variables for local development
    if use_bot:
        if SLACK_BOT_TOKEN:
            print(f"✅ Using bot token from environment variables")
            return WebClient(token=SLACK_BOT_TOKEN)
        raise ValueError(
            "❌ Slack Bot Token not provided. Options:\n"
            "1) Set SLACK_BOT_TOKEN in .env file\n"
            "2) Provide X-Slack-Bot-Token header\n"
            "3) Pass user_id with bot token in Supabase"
        )
    else:
        if SLACK_USER_TOKEN:
            print(f"✅ Using user token from environment variables")
            return WebClient(token=SLACK_USER_TOKEN)
        raise ValueError(
            "❌ Slack User Token not provided. Options:\n"
            "1) Provide user_id parameter (recommended)\n"
            "2) Send X-Slack-User-Token header\n"
            "3) Set SLACK_USER_TOKEN in .env file\n\n"
            "💡 Tip: Pass user_id='your-supabase-user-id' to fetch token automatically"
        )

# BOT token
@mcp.tool()
def slack_send_message(channel_id: str, text: str, ctx: Context, user_id: str = None) -> dict:
    """Send a message to a Slack channel."""
    client = get_slack_client_from_context(ctx, use_bot=True, user_id=user_id)
    try:
        response = client.chat_postMessage(channel=channel_id, text=text)
        return {"ok": True, "message_ts": response["ts"]}
    except SlackApiError as e:
        return {"ok": False, "error": str(e)}

# BOT token
@mcp.tool()
def slack_standup(user_name: str, channel_id: str, standup_text: str, ctx: Context, user_id: str = None) -> dict:
    """Post a standup update to a Slack channel."""
    client = get_slack_client_from_context(ctx, use_bot=True, user_id=user_id)
    try:
        message = f"👋 Hi {user_name}, starting your daily standup!\n{standup_text}"
        response = client.chat_postMessage(channel=channel_id, text=message)
        return {"ok": True, "message_ts": response["ts"], "message": message}
    except SlackApiError as e:
        return {"ok": False, "error": str(e)}

# USER token
@mcp.tool()
def slack_fetch_conversation_history(channel_id: str, limit: int = 10, ctx: Context = None, user_id: str = None) -> dict:
    """Fetch the latest messages from a channel as the authenticated user."""
    client = get_slack_client_from_context(ctx, use_bot=False, user_id=user_id)
    try:
        response = client.conversations_history(channel=channel_id, limit=limit)
        return {"ok": True, "messages": response["messages"]}
    except SlackApiError as e:
        return {"ok": False, "error": str(e)}

# BOT token
@mcp.tool()
def slack_list_users(ctx: Context, user_id: str = None) -> dict:
    """List all users in the workspace."""
    client = get_slack_client_from_context(ctx, use_bot=True, user_id=user_id)
    try:
        response = client.users_list()
        users = [
            {
                "id": u["id"],
                "name": u["real_name"],
                "email": u.get("profile", {}).get("email", "")
            }
            for u in response["members"]
        ]
        return {"ok": True, "users": users}
    except SlackApiError as e:
        return {"ok": False, "error": str(e)}

# USER token
@mcp.tool()
def slack_find_user_by_email(email: str, ctx: Context, user_id: str = None) -> dict:
    """Find a user by email."""
    client = get_slack_client_from_context(ctx, use_bot=False, user_id=user_id)
    try:
        response = client.users_lookupByEmail(email=email)
        return {"ok": True, "user": response["user"]}
    except SlackApiError as e:
        return {"ok": False, "error": str(e)}

# BOT token
@mcp.tool()
def slack_list_channels(ctx: Context, user_id: str = None) -> dict:
    """List all channels in the workspace."""
    client = get_slack_client_from_context(ctx, use_bot=True, user_id=user_id)
    try:
        response = client.conversations_list()
        channels = [{"id": c["id"], "name": c["name"]} for c in response["channels"]]
        return {"ok": True, "channels": channels}
    except SlackApiError as e:
        return {"ok": False, "error": str(e)}

# BOT token
@mcp.tool()
def slack_schedule_message(channel_id: str, text: str, post_at: str, ctx: Context, user_id: str = None) -> dict:
    """Schedule a message to be sent later (post_at is a Unix timestamp)."""
    client = get_slack_client_from_context(ctx, use_bot=True, user_id=user_id)
    try:
        response = client.chat_scheduleMessage(
            channel=channel_id,
            text=text,
            post_at=post_at
        )
        return {"ok": True, "scheduled_message_id": response["scheduled_message_id"]}
    except SlackApiError as e:
        return {"ok": False, "error": str(e)}

# BOT token
@mcp.tool()
def slack_create_channel(name: str, is_private: bool = False, invite_user_id: str = None, ctx: Context = None, user_id: str = None) -> dict:
    """Create a new Slack channel."""
    client = get_slack_client_from_context(ctx, use_bot=True, user_id=user_id)
    try:
        response = client.conversations_create(name=name, is_private=is_private)
        channel = response["channel"]
        channel_id = channel["id"]

        result = {
            "ok": True,
            "channel": {
                "id": channel_id,
                "name": channel["name"],
                "is_private": channel.get("is_private", False),
                "created": channel.get("created", 0)
            }
        }

        if invite_user_id:
            client.conversations_invite(channel=channel_id, users=invite_user_id)

        return result

    except SlackApiError as e:
        return {"ok": False, "error": str(e)}

# USER token
@mcp.tool()
def slack_open_dm(slack_user_id: str, ctx: Context, user_id: str = None) -> dict:
    """Open a direct message channel with a user as the authenticated user."""
    client = get_slack_client_from_context(ctx, use_bot=False, user_id=user_id)
    try:
        response = client.conversations_open(users=slack_user_id)
        return {"ok": True, "channel_id": response["channel"]["id"]}
    except SlackApiError as e:
        return {"ok": False, "error": str(e)}

# BOT token
@mcp.tool()
def slack_add_reaction(channel_id: str, timestamp: str, emoji: str, ctx: Context, user_id: str = None) -> dict:
    """Add a reaction (emoji) to a message."""
    client = get_slack_client_from_context(ctx, use_bot=True, user_id=user_id)
    try:
        client.reactions_add(channel=channel_id, timestamp=timestamp, name=emoji)
        return {"ok": True}
    except SlackApiError as e:
        return {"ok": False, "error": str(e)}

# USER token
@mcp.tool()
def slack_search_messages(channel_id: str, keyword: str, limit: int = 50, ctx: Context = None, user_id: str = None) -> dict:
    """Search messages by keyword as the authenticated user."""
    client = get_slack_client_from_context(ctx, use_bot=False, user_id=user_id)
    try:
        history = client.conversations_history(channel=channel_id, limit=limit)
        matched = [
            msg for msg in history["messages"]
            if keyword.lower() in msg.get("text", "").lower()
        ]
        return {"ok": True, "matches": matched}
    except SlackApiError as e:
        return {"ok": False, "error": str(e)}

# USER token
@mcp.tool()
def slack_get_user_profile(ctx: Context, user_id: str = None) -> dict:
    """Get the authenticated user's own Slack profile."""
    client = get_slack_client_from_context(ctx, use_bot=False, user_id=user_id)
    try:
        # First get auth info to know who the user is
        auth_response = client.auth_test()
        user_slack_id = auth_response["user_id"]
        
        # Then get their full profile
        response = client.users_profile_get(user=user_slack_id)
        return {
            "ok": True,
            "user_id": user_slack_id,
            "profile": response["profile"]
        }
    except SlackApiError as e:
        return {"ok": False, "error": str(e)}

# USER token
@mcp.tool()
def slack_list_user_conversations(limit: int = 100, ctx: Context = None, user_id: str = None) -> dict:
    """List all conversations the authenticated user is part of (channels, DMs, etc)."""
    client = get_slack_client_from_context(ctx, use_bot=False, user_id=user_id)
    try:
        response = client.users_conversations(limit=limit)
        conversations = [
            {
                "id": c["id"],
                "name": c.get("name", "DM"),
                "is_channel": c.get("is_channel", False),
                "is_group": c.get("is_group", False),
                "is_im": c.get("is_im", False),
                "is_private": c.get("is_private", False)
            }
            for c in response["channels"]
        ]
        return {"ok": True, "conversations": conversations}
    except SlackApiError as e:
        return {"ok": False, "error": str(e)}

if __name__ == "__main__":
    mcp.run(transport="sse", port=8000)
