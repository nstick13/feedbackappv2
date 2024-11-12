import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

message = Mail(
    from_email=os.environ['SENDGRID_FROM_EMAIL'],
    to_emails='nathan.stickney@gmail.com',
    subject='Test Email from SendGrid',
    html_content='<strong>This is a test email from SendGrid.</strong>'
)

try:
    sg = SendGridAPIClient(os.environ['SENDGRID_API_KEY'])
    response = sg.send(message)
    print(response.status_code)
    print(response.body)
    print(response.headers)
except Exception as e:
    print(str(e))