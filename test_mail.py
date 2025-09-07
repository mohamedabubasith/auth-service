from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import os

# Test SendGrid
def test_sendgrid():
    # Your API key
    api_key = "api-key"  # Replace with your actual key
    
    sg = SendGridAPIClient(api_key=api_key)
    
    message = Mail(
        from_email='mohamedabu.basith@gmail.com',  # Your verified sender
        to_emails='abubasith456@gmail.com',           # Test recipient
        subject='SendGrid Test',
        html_content='<p><strong>Success!</strong> SendGrid is working.</p>'
    )
    
    try:
        response = sg.send(message)
        print(f"✅ Success! Status: {response.status_code}")
        return True
    except Exception as e:
        print(f"❌ Failed: {str(e)}")
        return False

# Run test
if __name__ == "__main__":
    test_sendgrid()
