import resend
import os
from app.config import settings
from app.core.tenant_manager import TenantManager

# Initialize Resend with API key
resend.api_key = os.getenv("RESEND_API_KEY")

async def send_password_reset_email(to_email: str, reset_token: str, tenant_id: str):
    """Send password reset email using Resend (works on HF Spaces)"""
    
    # Get tenant info for personalization
    tenant_info = TenantManager.get_tenant_info(tenant_id)
    tenant_name = tenant_info.get("name", "Authentication Service")
    
    # ✅ Fixed reset URL
    reset_url = f"{settings.API_BASE_URL}/static/reset-password.html?token={reset_token}&tenant={tenant_id}"
    
    # Create HTML email content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Password Reset Request</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }}
            .content {{ padding: 20px 0; }}
            .button {{ display: inline-block; background-color: #007bff; color: white; 
                      padding: 12px 24px; text-decoration: none; border-radius: 4px; 
                      font-weight: bold; }}
            .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; 
                      color: #666; font-size: 14px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>🔐 Password Reset Request</h2>
                <p style="margin: 0; color: #666;">{tenant_name}</p>
            </div>
            
            <div class="content">
                <p>Hello,</p>
                
                <p>You requested a password reset for your <strong>{tenant_name}</strong> account 
                   associated with <strong>{to_email}</strong>.</p>
                
                <p>Click the button below to reset your password:</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}" class="button">Reset Password</a>
                </div>
                
                <p>Or copy and paste this link in your browser:</p>
                <p style="word-break: break-all; background-color: #f8f9fa; padding: 10px; border-radius: 4px;">
                    <a href="{reset_url}">{reset_url}</a>
                </p>
                
                <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; 
                           border-radius: 4px; margin: 20px 0;">
                    <p style="margin: 0;"><strong>⚠️ Important:</strong></p>
                    <ul style="margin: 10px 0;">
                        <li>This link will expire in <strong>1 hour</strong></li>
                        <li>Use it only once to reset your password</li>
                        <li>If you didn't request this, please ignore this email</li>
                    </ul>
                </div>
            </div>
            
            <div class="footer">
                <p>This is an automated message from {tenant_name} Authentication Service.</p>
                <p>If you're having trouble with the button, copy and paste the URL above into your web browser.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        # ✅ Send via Resend HTTP API instead of SMTP
        r = resend.Emails.send({
            "from": "noreply@yourdomain.com",  # Replace with your verified domain
            "to": to_email,
            "subject": f"Password Reset Request - {tenant_name}",
            "html": html_content
        })
        
        print(f"✅ Password reset email sent via Resend to {to_email} for tenant {tenant_id}")
        print(f"📧 Resend response: {r}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send password reset email to {to_email}: {str(e)}")
        return False

async def send_email(to_email: str, subject: str, html_content: str):
    """Generic email sending function using Resend"""
    try:
        r = resend.Emails.send({
            "from": "noreply@yourdomain.com",  # Replace with your verified domain
            "to": to_email,
            "subject": subject,
            "html": html_content
        })
        
        print(f"✅ Email sent via Resend to {to_email}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send email to {to_email}: {str(e)}")
        return False
