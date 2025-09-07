import resend
import os
import traceback
from app.config import settings
from app.core.tenant_manager import TenantManager

# Set API key from environment
resend.api_key = os.getenv("RESEND_API_KEY", "re_Y7wWD32x_Jj4qRj8oqBaYnwob7WqkcJPv")

async def send_password_reset_email(to_email: str, reset_token: str, tenant_id: str):
    """Send password reset email using Resend with enhanced error handling"""
    
    try:
        # Get tenant info
        tenant_info = TenantManager.get_tenant_info(tenant_id)
        tenant_name = tenant_info.get("name", "Authentication Service")
        
        # Create reset URL
        reset_url = f"{settings.API_BASE_URL}/static/reset-password.html?token={reset_token}&tenant={tenant_id}"
        
        # Your existing HTML content
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head><title>Password Reset Request</title></head>
        <body>
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2>🔐 Password Reset Request</h2>
                <p>Hello,</p>
                <p>You requested a password reset for your <strong>{tenant_name}</strong> account.</p>
                <p>Click the button below to reset your password:</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}" 
                       style="background-color: #007bff; color: white; padding: 12px 24px; 
                              text-decoration: none; border-radius: 4px; display: inline-block;">
                        Reset Password
                    </a>
                </div>
                
                <p>Or copy this link: <a href="{reset_url}">{reset_url}</a></p>
                <p><strong>This link expires in 1 hour.</strong></p>
                <p>If you didn't request this, please ignore this email.</p>
            </div>
        </body>
        </html>
        """
        
        print(f"🔄 Attempting to send email via Resend...")
        print(f"📧 From: onboarding@resend.dev")
        print(f"📧 To: {to_email}")
        print(f"🔑 API Key: {resend.api_key[:20]}..." if resend.api_key else "❌ No API Key")
        
        # ✅ Enhanced Resend call with better error capture
        response = resend.Emails.send({
            "from": "onboarding@resend.dev",
            "to": [to_email],  # Must be a list
            "subject": f"Password Reset Request - {tenant_name}",
            "html": html_content
        })
        
        # ✅ Print the actual response
        print(f"📧 Resend Raw Response: {response}")
        print(f"📧 Response Type: {type(response)}")
        
        # ✅ Check if response indicates success
        if response and hasattr(response, 'get'):
            if response.get('error'):
                print(f"❌ Resend API Error: {response['error']}")
                return False
            elif response.get('id'):
                print(f"✅ Email sent successfully! Message ID: {response['id']}")
                return True
        
        print(f"✅ Email sent to {to_email} for tenant {tenant_id}")
        return True
        
    except resend.exceptions.ResendError as re:
        # ✅ Specific Resend error handling
        print(f"❌ ResendError Details:")
        print(f"❌ Error Type: {type(re).__name__}")
        print(f"❌ Error Message: {str(re)}")
        print(f"❌ Error Args: {re.args}")
        
        # Try to get more details from the exception
        if hasattr(re, 'response'):
            print(f"❌ HTTP Response: {re.response}")
        if hasattr(re, 'status_code'):
            print(f"❌ Status Code: {re.status_code}")
        if hasattr(re, 'body'):
            print(f"❌ Response Body: {re.body}")
            
        return False
        
    except Exception as e:
        # ✅ Generic exception with full traceback
        print(f"❌ Generic Exception Details:")
        print(f"❌ Exception Type: {type(e).__name__}")
        print(f"❌ Exception Message: {str(e)}")
        print(f"❌ Exception Args: {e.args}")
        print(f"❌ Full Traceback:")
        traceback.print_exc()
        
        # Debug information
        print(f"❌ Debug Info:")
        print(f"   - API Key Set: {'Yes' if resend.api_key else 'No'}")
        print(f"   - API Key Format: {resend.api_key[:10]}... (len: {len(resend.api_key) if resend.api_key else 0})")
        print(f"   - Recipient Email: {to_email}")
        print(f"   - Tenant ID: {tenant_id}")
        
        return False
