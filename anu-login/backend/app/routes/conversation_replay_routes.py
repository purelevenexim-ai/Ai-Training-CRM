"""Conversation Replay Routes - Simple audit viewer

Endpoints:
- GET /api/admin/conversations - List conversations
- GET /api/admin/conversations/{phone} - View conversation replay
- GET /api/admin/conversations/{phone}/html - WhatsApp-style HTML replay
- GET /api/admin/routing-errors - View routing mismatches
- GET /api/admin/daily-report - View latest daily report
- GET /api/admin/daily-report/html - Formatted HTML report
"""

from fastapi import APIRouter, Query, HTTPException
from datetime import datetime, timezone, timedelta

from app.ai.audit_logger import get_conversation_history
from app.ai.routing_error_detector import get_routing_error_summary
from app.ai.daily_report_generator import get_latest_report
from app.storage import get_db_connection

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/conversations")
async def list_conversations(
    hours: int = Query(24, description="Last N hours of conversations"),
    limit: int = Query(50, description="Max conversations to return"),
):
    """List recent conversations"""
    try:
        conn = get_db_connection()
        
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        cutoff_iso = cutoff.isoformat()
        
        rows = conn.execute(
            """
            SELECT DISTINCT phone, MIN(created_at) as first_message, MAX(created_at) as last_message,
                   COUNT(*) as message_count
            FROM conversation_audit_log
            WHERE created_at >= ?
            GROUP BY phone
            ORDER BY last_message DESC
            LIMIT ?
            """,
            (cutoff_iso, limit),
        ).fetchall()
        
        conversations = []
        for row in rows:
            conversations.append({
                "phone": row['phone'],
                "first_message": row['first_message'],
                "last_message": row['last_message'],
                "message_count": row['message_count'],
                "view_url": f"/admin/conversations/{row['phone']}",
            })
        
        return {
            "total": len(conversations),
            "hours_lookback": hours,
            "conversations": conversations,
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{phone}")
async def view_conversation(phone: str):
    """
    View complete conversation replay for a phone number.
    
    Returns: Chronological list of all events (customer messages, routing, AI responses, etc.)
    """
    try:
        history = get_conversation_history(phone, limit=500)
        
        if not history:
            raise HTTPException(status_code=404, detail=f"No conversation history for {phone}")
        
        # Build a chat-like structure
        events = []
        current_owner = None
        current_flow = None
        
        for event in history:
            event_obj = {
                "timestamp": event['timestamp'],
                "type": event['source'],  # "customer", "ai", "wabis", "system", "human"
                "direction": event['direction'],  # "inbound" or "outbound"
                "message": event['message'],
                "owner_before": event['owner_before'],
                "owner_after": event['owner_after'],
                "active_flow": event['active_flow'],
                "detected_intent": event['detected_intent'],
                "route_decision": event['route_decision'],
                "reason": event['reason'],
                "metadata": event['metadata'],
            }
            
            if event['owner_after']:
                current_owner = event['owner_after']
            if event['active_flow']:
                current_flow = event['active_flow']
            
            events.append(event_obj)
        
        return {
            "phone": phone,
            "total_events": len(events),
            "current_owner": current_owner,
            "current_flow": current_flow,
            "events": events,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{phone}/html")
async def view_conversation_html(phone: str):
    """
    View conversation replay as HTML (WhatsApp-style chat).
    """
    try:
        history = get_conversation_history(phone, limit=500)
        
        if not history:
            return f"<html><body><h1>No conversation history for {phone}</h1></body></html>"
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Conversation Replay - {phone}</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }}
        
        .container {{
            max-width: 600px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 18px;
            margin-bottom: 5px;
        }}
        
        .header p {{
            font-size: 12px;
            opacity: 0.9;
        }}
        
        .messages {{
            padding: 20px;
            height: 500px;
            overflow-y: auto;
            background: #f0f0f0;
        }}
        
        .message {{
            margin-bottom: 15px;
            display: flex;
            animation: fadeIn 0.3s ease-in;
        }}
        
        @keyframes fadeIn {{
            from {{ opacity: 0; }}
            to {{ opacity: 1; }}
        }}
        
        .message.inbound {{
            justify-content: flex-start;
        }}
        
        .message.outbound {{
            justify-content: flex-end;
        }}
        
        .bubble {{
            max-width: 70%;
            padding: 10px 12px;
            border-radius: 12px;
            word-wrap: break-word;
            font-size: 14px;
            line-height: 1.4;
        }}
        
        .message.inbound .bubble {{
            background: white;
            border: 1px solid #ddd;
        }}
        
        .message.outbound .bubble {{
            background: #dcf8c6;
        }}
        
        .message.system .bubble {{
            background: #f0f0f0;
            border: 1px solid #ccc;
            font-size: 12px;
            text-align: center;
            width: 100%;
        }}
        
        .timestamp {{
            font-size: 12px;
            color: #999;
            margin-top: 3px;
            margin-left: 5px;
        }}
        
        .source-badge {{
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 3px;
            margin-right: 5px;
            font-weight: bold;
        }}
        
        .source-customer {{ background: #e8f5e9; color: #2e7d32; }}
        .source-ai {{ background: #e3f2fd; color: #1565c0; }}
        .source-wabis {{ background: #f3e5f5; color: #6a1b9a; }}
        .source-human {{ background: #fff3e0; color: #e65100; }}
        .source-system {{ background: #f5f5f5; color: #424242; }}
        
        .metadata {{
            font-size: 11px;
            color: #666;
            margin-top: 3px;
        }}
        
        .footer {{
            background: #f9f9f9;
            padding: 15px 20px;
            border-top: 1px solid #ddd;
            font-size: 12px;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Conversation Replay</h1>
            <p>Phone: {phone}</p>
        </div>
        
        <div class="messages">
"""
        
        for event in history:
            timestamp = event['timestamp'][:19] if event['timestamp'] else ''
            
            direction = event['direction']
            source = event['source']
            message = event['message'] or ''
            
            # Determine message class
            msg_class = "system"
            if direction == "inbound":
                msg_class = "inbound"
            elif direction == "outbound":
                msg_class = "outbound"
            
            # Escape HTML
            message = message.replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>')
            
            # Source badge
            source_badge = f'<span class="source-badge source-{source}">{source}</span>'
            
            # Metadata
            metadata_str = ""
            if event.get('detected_intent'):
                metadata_str += f"Intent: {event['detected_intent']} "
            if event.get('route_decision'):
                metadata_str += f"Route: {event['route_decision']} "
            if event.get('active_flow'):
                metadata_str += f"Flow: {event['active_flow']}"
            
            metadata_html = f'<div class="metadata">{metadata_str}</div>' if metadata_str else ''
            
            html += f"""
            <div class="message {msg_class}">
                <div style="text-align: {'right' if msg_class == 'outbound' else 'left'}; width: 100%;">
                    {source_badge}
                    <span style="font-size: 12px; color: #999;">{timestamp}</span>
                    <div class="bubble">{message}</div>
                    {metadata_html}
                </div>
            </div>
"""
        
        html += """
        </div>
        
        <div class="footer">
            <p><strong>Conversation Audit Trail</strong></p>
            <p>View all customer messages, routing decisions, AI responses, and state changes.</p>
        </div>
    </div>
</body>
</html>
"""
        
        return html
    
    except Exception as e:
        return f"<html><body><h1>Error: {str(e)}</h1></body></html>"


@router.get("/routing-errors")
async def view_routing_errors(hours: int = Query(24, description="Last N hours")):
    """
    View routing errors detected in recent conversations.
    
    Returns: List of routing mismatches (where actual route != expected route)
    """
    try:
        summary = get_routing_error_summary(hours)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/daily-report")
async def view_daily_report():
    """Get latest daily conversation report"""
    try:
        report = get_latest_report()
        return {"content": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/daily-report/html")
async def view_daily_report_html():
    """Get daily report as formatted HTML"""
    try:
        report = get_latest_report()
        
        # Convert markdown to simple HTML
        html_lines = []
        in_code_block = False
        in_table = False
        
        for line in report.split('\n'):
            if line.startswith('```'):
                in_code_block = not in_code_block
                if in_code_block:
                    html_lines.append('<pre>')
                else:
                    html_lines.append('</pre>')
            elif line.startswith('|') and not in_code_block:
                if not in_table:
                    html_lines.append('<table border="1" style="border-collapse: collapse; margin: 10px 0;">')
                    in_table = True
                html_lines.append('<tr>')
                for cell in line.split('|')[1:-1]:
                    html_lines.append(f'<td style="padding: 8px;">{cell.strip()}</td>')
                html_lines.append('</tr>')
            elif line.startswith('---'):
                if in_table:
                    html_lines.append('</table>')
                    in_table = False
                html_lines.append('<hr style="margin: 20px 0; border: none; border-top: 2px solid #ddd;">')
            elif line.startswith('# '):
                html_lines.append(f'<h1 style="margin-top: 20px;">{line[2:]}</h1>')
            elif line.startswith('## '):
                html_lines.append(f'<h2 style="margin-top: 15px;">{line[3:]}</h2>')
            elif line.startswith('### '):
                html_lines.append(f'<h3 style="margin-top: 10px;">{line[4:]}</h3>')
            elif line.startswith('- '):
                html_lines.append(f'<li>{line[2:]}</li>')
            elif line.startswith('**') and line.endswith('**'):
                html_lines.append(f'<strong>{line[2:-2]}</strong><br>')
            elif line.startswith('*') and line.endswith('*'):
                html_lines.append(f'<em>{line[1:-1]}</em><br>')
            elif in_code_block:
                html_lines.append(line)
            elif line.strip():
                html_lines.append(f'<p>{line}</p>')
        
        if in_table:
            html_lines.append('</table>')
        
        html_content = '\n'.join(html_lines)
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Daily Conversation Report</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #f5f5f5;
            padding: 20px;
            color: #333;
        }}
        
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 40px;
        }}
        
        h1 {{ color: #2c3e50; margin-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        h3 {{ color: #7f8c8d; margin-top: 15px; }}
        
        p {{ line-height: 1.6; margin: 10px 0; }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        
        table td {{ 
            padding: 8px 12px;
            border: 1px solid #ecf0f1;
        }}
        
        table tr:nth-child(2n) {{
            background: #f8f9fa;
        }}
        
        ul {{ margin-left: 20px; margin: 10px 0; }}
        li {{ margin: 5px 0; }}
        
        code {{
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
        }}
        
        pre {{
            background: #f4f4f4;
            padding: 10px;
            border-radius: 4px;
            overflow-x: auto;
            margin: 10px 0;
        }}
        
        em {{ color: #e74c3c; font-style: italic; }}
        strong {{ color: #2980b9; font-weight: bold; }}
        
        hr {{
            margin: 20px 0;
            border: none;
            border-top: 2px solid #ddd;
        }}
    </style>
</head>
<body>
    <div class="container">
        {html_content}
    </div>
</body>
</html>
"""
        return html
    
    except Exception as e:
        return f"<html><body><h1>Error: {str(e)}</h1></body></html>"
