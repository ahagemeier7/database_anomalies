from typing import List
from anomaly_handler.test.consumer.consumer import anomaly_consumer_kafka


class anomaly_handler:
  
  def __init__(self,target_table:str,group_id:str,columns_to_ignore: List[str]):
    self.target_table = target_table

    self.group_id = group_id
    self.columns_to_ignore = columns_to_ignore or ['id']

  def handle_anomaly(self):
    KAFKA_TOPIC = f"source-postgres.public.{self.target_table}"

    for event_json in anomaly_consumer_kafka(
      topico=KAFKA_TOPIC,
      group_id=self.group_id
      ):
      pass


