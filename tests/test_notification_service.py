import unittest
from unittest.mock import patch, MagicMock
import smtplib
from queue import Queue
import logging
from notification_service import EmailNotificationService, EmailMessage
from flask import current_app

class TestEmailNotificationService(unittest.TestCase):
    def setUp(self):
        self.email_service = EmailNotificationService()
        self.test_message = EmailMessage(
            subject="Test Subject",
            recipients=["test@example.com"],
            html_content="<p>Test content</p>"
        )

    @patch('smtplib.SMTP')
    def test_smtp_connection_success(self, mock_smtp):
        """Test successful SMTP connection"""
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        
        with self.email_service._create_smtp_connection() as server:
            self.assertIsNotNone(server)
            mock_smtp.assert_called_once()
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once()

    @patch('smtplib.SMTP')
    def test_smtp_connection_timeout(self, mock_smtp):
        """Test SMTP connection timeout handling"""
        mock_smtp.side_effect = smtplib.SMTPConnectError(424, "Connection timed out")
        
        with self.assertRaises(smtplib.SMTPConnectError):
            self.email_service._create_smtp_connection()

    @patch('smtplib.SMTP')
    def test_smtp_authentication_error(self, mock_smtp):
        """Test SMTP authentication error handling"""
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, "Invalid credentials")
        
        with self.assertRaises(smtplib.SMTPAuthenticationError):
            self.email_service._create_smtp_connection()

    @patch.object(EmailNotificationService, 'send_email')
    def test_email_queue_processing(self, mock_send_email):
        """Test email queue processing with retries"""
        mock_send_email.side_effect = [False, False, True]  # Fail twice, succeed on third try
        
        self.email_service.queue_email(self.test_message)
        self.assertEqual(self.email_service.email_queue.qsize(), 1)
        
        # Process the queue
        self.email_service._process_email_queue()
        mock_send_email.assert_called_with(self.test_message)
        self.assertEqual(mock_send_email.call_count, 3)

    @patch('smtplib.SMTP')
    def test_send_email_success(self, mock_smtp):
        """Test successful email sending"""
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        
        result = self.email_service.send_email(self.test_message)
        self.assertTrue(result)
        mock_server.send_message.assert_called_once()

    @patch('smtplib.SMTP')
    def test_send_email_server_disconnect(self, mock_smtp):
        """Test handling of server disconnection during send"""
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        mock_server.send_message.side_effect = smtplib.SMTPServerDisconnected()
        
        result = self.email_service.send_email(self.test_message)
        self.assertFalse(result)

    def test_queue_email_validation(self):
        """Test email queuing with invalid input"""
        invalid_message = EmailMessage(
            subject="",  # Invalid empty subject
            recipients=[],  # Invalid empty recipients
            html_content=""  # Invalid empty content
        )
        
        with self.assertLogs(level='ERROR') as log:
            self.email_service.queue_email(invalid_message)
            self.assertIn("Error queueing email", log.output[0])

if __name__ == '__main__':
    unittest.main()
