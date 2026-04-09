import os
import smtplib
import logging
from email.message import EmailMessage
from ..consumer.consumer import anomaly_consumer_kafka

class AnomalyHandler:
  
  def __init__(self,group_id:str):
    self.group_id = group_id

    self.sender_email = os.getenv("SENDER_EMAIL")
    self.reciever_email = os.getenv("RECIEVER_EMAIL")
    self.password = os.getenv("EMAIL_PASSWORD")

  def handle_anomalies(self):
    KAFKA_TOPIC = f"detected_anomalies"

    for event_json in anomaly_consumer_kafka(
      topic=KAFKA_TOPIC,
      group_id=self.group_id
      ):
      
      msg = self._email_assembler(event_json)

      try:
        with smtplib.SMTP_SSL('smtp.gmail.com',465) as smtp:
          smtp.login(self.sender_email,self.password)
          smtp.send_message(msg)
      except Exception as e:
        logging.error(f"Failed to send detection email: {e}")

  def _email_assembler(self,event_json) -> EmailMessage:

    msg =  EmailMessage()
    msg['Subject'] = "Anomaly Detected"
    msg['From'] = self.sender_email
    msg['To'] = self.reciever_email

    status_color = "#f39c12" if event_json['status'] == 'pending_revision' else "#e74c3c"
  
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; background-color: #f4f4f7; padding: 20px;">
        <div style="max-width: 600px; margin: auto; background: #ffffff; border-radius: 8px; overflow: hidden; border: 1px solid #e1e1e1; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            
            <div style="background-color: #2c3e50; padding: 20px; text-align: center;">
                <h2 style="color: #ffffff; margin: 0;">Anomaly Detection Alert</h2>
            </div>

            <div style="padding: 30px;">
                <p style="font-size: 16px;">An automated detection system has identified a potential anomaly in the database stream.</p>
                
                <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                    <tr>
                        <td style="padding: 8px 0; font-weight: bold; width: 40%;">Alert ID:</td>
                        <td style="padding: 8px 0; color: #2980b9;">{event_json.get('id', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; font-weight: bold;">Detection Time:</td>
                        <td style="padding: 8px 0;">{event_json.get('timestamp_detection', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; font-weight: bold;">Status:</td>
                        <td><span style="background-color: {status_color}; color: white; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: bold;">{event_json.get('status', 'unknown').upper()}</span></td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; font-weight: bold;">ML Model:</td>
                        <td style="padding: 8px 0; font-style: italic;">{event_json.get('ml_model', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; font-weight: bold;">Source:</td>
                        <td style="padding: 8px 0;">{event_json.get('origin', {{}}).get('table', 'N/A')} (via {event_json.get('origin', {{}}).get('source_topic', 'N/A')})</td>
                    </tr>
                </table>

                <h4 style="margin-bottom: 10px; border-bottom: 1px solid #eee; padding-bottom: 5px;">Raw Event Data</h4>
                <pre style="background: #272822; color: #f8f8f2; padding: 15px; border-radius: 5px; font-size: 12px; overflow-x: auto;">
                {event_json.get('raw_event', 'No raw data available')}
                </pre>

                <div style="margin-top: 30px; text-align: center;">
                    <a href="#" style="background-color: #2980b9; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">Review in Dashboard</a>
                </div>
            </div>

            <div style="background-color: #f9f9f9; padding: 15px; text-align: center; font-size: 12px; color: #777;">
                Sent by Automated Security Monitor • {event_json.get('timestamp_detection', '')}
            </div>
        </div>
    </body>
    </html>
    """

    msg.set_content("A database anomaly was detected. Please use an HTML-compatible email client to view details.")
    msg.add_alternative(html_content, subtype='html')

    return msg
