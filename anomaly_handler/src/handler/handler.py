import os
import smtplib
import logging
from email.message import EmailMessage
from sqlalchemy import text
from ..consumer.consumer import anomaly_consumer_kafka
from ..db.db import get_db_engine
import json

class AnomalyHandler:
  
  def __init__(self,group_id:str):
    self.group_id = group_id

    self.sender_email = os.getenv("SENDER_EMAIL")
    self.reciever_email = os.getenv("RECIEVER_EMAIL")
    self.password = os.getenv("EMAIL_PASSWORD")

    self.db_engine = get_db_engine()

    self._create_history_table()


  def handle_anomalies(self):
    KAFKA_TOPIC = f"detected_anomalies"

    for event_json in anomaly_consumer_kafka(
      topic=KAFKA_TOPIC,
      group_id=self.group_id
      ):

      alert_id = event_json.get('id', 'N/A')
      table = event_json.get('origin', {}).get('table', 'unknown_table')
      model = event_json.get('ml_model', 'N/A')
      

      raw_event = event_json.get('raw_event', {})
      db_record_id = raw_event.get('id', 'N/A')

      logging.warning(
          f"🚨 ANOMALY CAUGHT! Alert: [{alert_id}] | "
          f"Table: '{table}' (Record ID: {db_record_id}) | "
          f"Model: {model} | Action: Dispatching Email..."
        )

      self._save_to_db(event_json)

      msg = self._email_assembler(event_json)

      try:
        with smtplib.SMTP_SSL('smtp.gmail.com',465) as smtp:
          smtp.login(self.sender_email,self.password)
          smtp.send_message(msg)
      except Exception as e:
        logging.error(f"Failed to send detection email: {e}")
  
  def _email_assembler(self, event_json) -> EmailMessage:
      msg = EmailMessage()
      msg['Subject'] = "Anomaly Detected"
      msg['From'] = self.sender_email
      msg['To'] = self.reciever_email

      # 1. Tratamento de variáveis LIMPO (Fora da f-string)
      status = event_json.get('status', 'unknown')
      status_color = "#f39c12" if status == 'pending_revision' else "#e74c3c"
    
      alert_id = event_json.get('id', 'N/A')
      timestamp = event_json.get('timestamp_detection', 'N/A')
      ml_model = event_json.get('ml_model', 'N/A')
        
      # Extraindo com segurança a Origem
      origin = event_json.get('origin', {})
      table_name = origin.get('table', 'N/A')
      source_topic = origin.get('source_topic', 'N/A')

      raw_event_formatted = json.dumps(event_json.get('raw_event', {}), indent=4, ensure_ascii=False)

      # 2. HTML limpo e fácil de ler
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
                          <td style="padding: 8px 0; color: #2980b9;">{alert_id}</td>
                      </tr>
                      <tr>
                          <td style="padding: 8px 0; font-weight: bold;">Detection Time:</td>
                          <td style="padding: 8px 0;">{timestamp}</td>
                      </tr>
                      <tr>
                          <td style="padding: 8px 0; font-weight: bold;">Status:</td>
                          <td><span style="background-color: {status_color}; color: white; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: bold;">{status.upper()}</span></td>
                      </tr>
                      <tr>
                          <td style="padding: 8px 0; font-weight: bold;">ML Model:</td>
                          <td style="padding: 8px 0; font-style: italic;">{ml_model}</td>
                      </tr>
                      <tr>
                          <td style="padding: 8px 0; font-weight: bold;">Source:</td>
                          <td style="padding: 8px 0;">{table_name} (via {source_topic})</td>
                      </tr>
                  </table>
                   <h4 style="margin-bottom: 10px; border-bottom: 1px solid #eee; padding-bottom: 5px;">Raw Event Data</h4>
                 <pre style="background: #272822; color: #f8f8f2; padding: 15px; border-radius: 5px; font-size: 12px; overflow-x: auto;">{raw_event_formatted}</pre>
                  <div style="margin-top: 30px; text-align: center;">
                      <a href="#" style="background-color: #2980b9; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">Review in Dashboard</a>
                  </div>
              </div>

              <div style="background-color: #f9f9f9; padding: 15px; text-align: center; font-size: 12px; color: #777;">
                  Sent by Automated Security Monitor • {timestamp}
              </div>
          </div>
      </body>
      </html>
      """

      msg.set_content("A database anomaly was detected. Please use an HTML-compatible email client to view details.")
      msg.add_alternative(html_content, subtype='html')

      return msg
    
  def _create_history_table(self):
      """Create the anomalies_history table"""
      query = text("""
          CREATE TABLE IF NOT EXISTS anomalies_history (
              alert_id VARCHAR(100) PRIMARY KEY,
              timestamp_detection TIMESTAMP,
              origin_table VARCHAR(100),
              source_topic VARCHAR(200),
              ml_model VARCHAR(100),
              status VARCHAR(50),
              raw_event JSONB 
          );
      """)
      try:
          with self.db_engine.connect() as conn:
              conn.execute(query)
              conn.commit()
      except Exception as e:
          logging.error(f"Failed to create anomalies_history table: {e}")

  def _save_to_db(self, event_json):
      """Saving the json into postgres"""
      query = text("""
          INSERT INTO anomalies_history 
          (alert_id, timestamp_detection, origin_table, source_topic, ml_model, status, raw_event)
          VALUES 
          (:alert_id, :timestamp_detection, :origin_table, :source_topic, :ml_model, :status, :raw_event)
          ON CONFLICT (alert_id) DO NOTHING; 
      """)
      
      params = {
          "alert_id": event_json.get('id', 'N/A'),
          "timestamp_detection": event_json.get('timestamp_detection'),
          "origin_table": event_json.get('origin', {}).get('table', 'unknown'),
          "source_topic": event_json.get('origin', {}).get('source_topic', 'unknown'),
          "ml_model": event_json.get('ml_model', 'N/A'),
          "status": event_json.get('status', 'unknown'),
          #"raw_event": json.dumps(event_json.get('raw_event', {}))
          "raw_event": event_json.get('raw_event', {})
      }

      try:
          with self.db_engine.connect() as conn:
              conn.execute(query, params)
              conn.commit()
          logging.info(f"Anomaly[{params['alert_id']}] successfully saved to database.")
      except Exception as e:
          logging.error(f"Database insertion failed for anomaly [{params['alert_id']}]: {e}")