from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import os
from app.config import settings
from app.core.tenant_manager import TenantManager

# Initialize SendGrid
sg = SendGridAPIClient(api_key="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")

async def send_password_reset_email(to_email: str, reset_token: str, tenant_id: str):
    """Send password reset email using SendGrid"""
    
    try:
        # Get tenant info
        tenant_info = TenantManager.get_tenant_info(tenant_id)
        tenant_name = tenant_info.get("name", "Authentication Service")
        
        # Create reset URL
        reset_url = f"{settings.API_BASE_URL}/static/reset-password.html?token={reset_token}&tenant={tenant_id}"
        
        # HTML content (same as before)
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head><title>Password Reset Request</title></head>
        <body>
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2>🔐 Password Reset Request</h2>
                <p>Hello,</p>
                <p>You requested a password reset for your <strong>{tenant_name}</strong> account.</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}" 
                       style="background-color: #007bff; color: white; padding: 12px 24px; 
                              text-decoration: none; border-radius: 4px; display: inline-block;">
                        Reset Password
                    </a>
                </div>
                
                <p>Or copy this link: <a href="{reset_url}">{reset_url}</a></p>
                <p><strong>This link expires in 1 hour.</strong></p>
            </div>
        </body>
        </html>
        """
        
        print(f"🔄 Sending email via SendGrid to {to_email}...")
        
        # ✅ SendGrid email
        message = Mail(
            from_email='mohamedabu.basith@gmail.com',  # Change to verified sender
            to_emails=to_email,
            subject=f'Password Reset Request - {tenant_name}',
            html_content=html_content
        )
        
        response = sg.send(message)
        
        print(f"📧 SendGrid Response Status: {response.status_code}")
        print(f"📧 SendGrid Response Body: {response.body}")
        print(f"📧 SendGrid Response Headers: {response.headers}")
        
        if response.status_code == 202:  # SendGrid success code
            print(f"✅ Password reset email sent via SendGrid to {to_email}")
            return True
        else:
            print(f"❌ SendGrid failed with status: {response.status_code}")
            return False
        
    except Exception as e:
        print(f"❌ SendGrid Error Details:")
        print(f"   - Type: {type(e).__name__}")
        print(f"   - Message: {str(e)}")
        return False

async def send_email(to_email: str, subject: str, html_content: str):
    """Generic email sending via SendGrid"""
    try:
        message = Mail(
            from_email='mohamedabu.basith@gmail.com',
            to_emails=to_email,
            subject=subject,
            html_content=html_content
        )
        
        response = sg.send(message)
        
        if response.status_code == 202:
            print(f"✅ Email sent via SendGrid to {to_email}")
            return True
        else:
            print(f"❌ SendGrid failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ SendGrid error: {str(e)}")
        return False
