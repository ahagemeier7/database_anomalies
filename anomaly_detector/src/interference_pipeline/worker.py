import os
import joblib
import logging
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy import text
from ..training_pipeline.db.db_internal import get_db_engine
from ..training_pipeline.workers.model_versioning import get_active_model_version, get_model_version
from .preprocessing_data.preprocess_data import DynamicPreprocessor
from .consumer.consumer import consumer_kafka_stream
from .producer.producer import AnomalyProducer
from sklearn.ensemble import IsolationForest,RandomForestClassifier


class Worker:

  def __init__(self,target_table:str,group_id:str,columns_to_ignore: List[str],date_columns:List[str] = None, model_version: Optional[str] = None, inference_mode: Optional[str] = None):
    self.target_table = target_table
    self.group_id = group_id
    self.columns_to_ignore = columns_to_ignore or ['id']
    self.date_columns = date_columns or []
    self.model_version = model_version
    self.inference_mode = self._normalize_inference_mode(inference_mode)
    self.anomaly_producer = AnomalyProducer()

    self.preprocessor: DynamicPreprocessor = None
    self.model_if: IsolationForest = None
    self.model_rf: RandomForestClassifier = None

    self.last_active_version: Optional[str] = None
    self.last_model_files_mtime: dict[str, float] = {}
    self.last_inference_mode = self.inference_mode

    self.base_models_dir = self._resolve_models_dir()
    self.ISOLATIONFOREST_MODEL_PATH = os.path.join(self.base_models_dir, f"{self.target_table}_if_model.pkl")
    self.RANDOMFOREST_MODEL_PATH = os.path.join(self.base_models_dir, f"{self.target_table}_rf_model.pkl")
    self.TRANSLATOR_PATH = os.path.join(self.base_models_dir, f"{self.target_table}_translator.pkl")
    self.SCALER_PATH = os.path.join(self.base_models_dir, f"{self.target_table}_scaler.pkl")
    self.USE_VERSIONED_MODEL = False

    self.RF_HIGH_CONFIDENCE_THRESHOLD = 0.85   # RF alone triggers the anomaly
    self.RF_MODERATE_THRESHOLD = 0.4           # RF + IF combined
    self.IF_COMBINED_THRESHOLD = 0.0           # IF to combined vote (negative decision_function = anomaly)
    self.IF_STANDALONE_THRESHOLD = 0.0         # IF triggers anomaly when decision_function < 0

  def _resolve_models_dir(self) -> str:
    candidates = []
    cwd = os.getcwd()
    if cwd:
      candidates.append(os.path.join(cwd, "models"))
      candidates.append(os.path.join(cwd, "src", "models"))
    candidates.extend([
      os.path.join("/app", "models"),
      os.path.join("/app", "src", "models"),
      os.path.join(os.path.dirname(__file__), "..", "..", "src", "models"),
      os.path.join(os.path.dirname(__file__), "..", "models"),
    ])

    for candidate in candidates:
      if os.path.isdir(candidate):
        return candidate

    return os.path.join(cwd or ".", "models")

  def _normalize_inference_mode(self, inference_mode: Optional[str]) -> str:
    if inference_mode is None:
      return "hybrid"

    normalized = str(inference_mode).strip().lower()

    if normalized in {"if", "isolation_forest", "isolationforest"}:
      return "if"
    if normalized in {"rf", "random_forest", "randomforest"}:
      return "rf"
    if normalized in {"hybrid", "hybrid_model"}:
      return "hybrid"

    logging.warning("Unsupported inference mode '%s'. Falling back to 'hybrid'.", inference_mode)
    return "hybrid"

  def _sync_inference_mode_from_db(self, reload_models: bool = False) -> None:
    try:
      engine = get_db_engine()
      with engine.connect() as conn:
        row = conn.execute(
          text("""
            SELECT inference_mode
            FROM pipelines_config
            WHERE target_table = :target_table
          """),
          {"target_table": self.target_table},
        ).mappings().first()

      if row and row.get("inference_mode"):
        normalized_mode = self._normalize_inference_mode(row["inference_mode"])
        if normalized_mode != self.inference_mode:
          self.inference_mode = normalized_mode
          logging.info("Inference mode updated from DB to '%s'.", self.inference_mode)
          if reload_models and self.preprocessor is not None:
            logging.info("Reloading models because inference mode changed.")
            self._load_models()
    except Exception as exc:
      logging.warning("Could not sync inference mode from DB: %s", exc)

  def _check_active_version_changed(self) -> bool:
    """Check the DB to see if a different model version is now active.
    Only triggers after the initial load (when last_active_version is set)."""
    if self.last_active_version is None:
      return False
    try:
      engine = get_db_engine()
      active = get_active_model_version(engine, self.target_table)
      if active and active["version"] != self.last_active_version:
        logging.info(
          "Active model version changed from '%s' to '%s'. Reloading...",
          self.last_active_version, active["version"],
        )
        return True
    except Exception as exc:
      logging.warning("Could not check active version from DB: %s", exc)
    return False

  def _check_model_files_changed(self) -> bool:
    """Check if any loaded model file has a newer mtime on disk."""
    model_paths_to_check = [
        self.ISOLATIONFOREST_MODEL_PATH,
        self.TRANSLATOR_PATH,
        self.SCALER_PATH,
    ]
    if self.RANDOMFOREST_MODEL_PATH:
        model_paths_to_check.append(self.RANDOMFOREST_MODEL_PATH)

    for path in model_paths_to_check:
        if os.path.exists(path):
            current_mtime = os.path.getmtime(path)
            last_mtime = self.last_model_files_mtime.get(path, 0)
            if current_mtime > last_mtime:
                logging.warning("Model file changed: %s, reloading...", path)
                return True
    return False

  def start_detection(self) -> None:
    self._register_pipeline()
    
    if not self._load_models():
      return
    KAFKA_TOPIC = f"source-postgres.public.{self.target_table}"

    
    logging.info(f"Worker started for the {self.target_table} pipeline.")

    for event_json in consumer_kafka_stream(
      topic=KAFKA_TOPIC,
      group_id=self.group_id
    ):
      try:
        self._sync_inference_mode_from_db(reload_models=True)

        # Check if active model version changed in DB (versioned mode)
        # or if any model file was updated on disk (legacy/latest mode)
        if self._check_active_version_changed() or self._check_model_files_changed():
            self._load_models()
            logging.warning("Reload complete")
          
        logging.info(f"Stream received from Kafka! Processing payload ID: {event_json.get('id', 'Unknown')}")
        features = self.preprocessor.transform_json_to_features(event_json)

        score_if = None
        prob_rf = None

        if self.inference_mode in {"if", "hybrid"} and self.model_if is not None:
          score_if = self.model_if.decision_function(features)[0]

        if self.inference_mode in {"rf", "hybrid"} and self.model_rf is not None:
          prob_rf = self.model_rf.predict_proba(features)[0][1]
          
        is_anomaly = self._judge_prediction(score_if=score_if, prob_rf=prob_rf)
          

        if is_anomaly == True:
          logging.info("Anomaly detected, sending to kafka")

          for col in self.date_columns:
            date_value = event_json.get(col)
            if date_value and isinstance(date_value, int):
              # Converting microseconds to date 
              dt = datetime.fromtimestamp(date_value / 1_000_000.0, tz=timezone.utc)
              event_json[col] = dt.strftime('%d/%m/%Y %H:%M:%S')

          if self.inference_mode == "rf":
            model_used = "RandomForest_v1"
          elif self.inference_mode == "if":
            model_used = "IsolationForest_v1"
          else:
            model_used = "Hybrid (RF+IF)"

          payload_anomaly = {
            "id": f"ALRT-{event_json.get('id', 'N/A')}",
            "timestamp_detection": datetime.now(timezone.utc).isoformat(),
            "origin": {
                "table": self.target_table,
                "source_topic": KAFKA_TOPIC
            },
            "ml_model": model_used,
            "status": "pending_revision",
            "raw_event": event_json 
          }
          
          self.anomaly_producer.send_anomaly(
            topic="detected_anomalies", 
            payload=payload_anomaly
          )

      except Exception as e:
        logging.error(f"An unexpected error occured while predicting the features: {e}")
      
  def _judge_prediction(self,score_if:float,prob_rf:float = None) -> bool:
    """Decide whether an event is anomalous using the selected inference mode."""
    if self.inference_mode == "rf":
      return prob_rf is not None and prob_rf > self.RF_HIGH_CONFIDENCE_THRESHOLD

    if self.inference_mode == "if":
      return score_if is not None and score_if < self.IF_STANDALONE_THRESHOLD

    if prob_rf is not None:
      #If Random forest has more than 85% sure, the event is an anomaly
      if prob_rf > self.RF_HIGH_CONFIDENCE_THRESHOLD:
        return True
      
      #If Random forest was not so sure on the event, but Isolation forest thought it was a weird event,then is an anomaly
      if prob_rf > self.RF_MODERATE_THRESHOLD and score_if is not None and score_if < self.IF_COMBINED_THRESHOLD: 
        return True
    
    return score_if is not None and score_if < self.IF_STANDALONE_THRESHOLD
  
  def _load_models(self):
    """Loads all available models and preprocessor at startup."""

    self._sync_inference_mode_from_db()

    engine = get_db_engine()
    version_record = None

    if self.model_version:
      logging.info(f"Looking for explicit model version '%s' in the internal DB...", self.model_version)
      version_record = get_model_version(engine, self.target_table, self.model_version)

    if not version_record:
      logging.info("Looking for the active model version in the internal DB...")
      version_record = get_active_model_version(engine, self.target_table)

    if version_record:
      logging.info(
          "Found versioned model record for table '%s': %s",
          self.target_table,
          version_record["version"],
      )
      self.USE_VERSIONED_MODEL = True
      self.TRANSLATOR_PATH = version_record["translator_path"]
      self.ISOLATIONFOREST_MODEL_PATH = version_record["if_model_path"]
      self.SCALER_PATH = version_record["scaler_path"]
      self.RANDOMFOREST_MODEL_PATH = version_record.get("rf_model_path") or ""
    else:
      logging.warning(
          "No versioned model record found for '%s'. Falling back to legacy model paths.",
          self.target_table,
      )

    logging.info("Selected inference mode: %s", self.inference_mode)

    try:
      self.preprocessor = DynamicPreprocessor(
        table_name=self.target_table,
        columns_to_ignore=self.columns_to_ignore,
        translator_path=self.TRANSLATOR_PATH,
        scaler_path=self.SCALER_PATH,
      )
    except FileNotFoundError as exc:
      logging.error("Failed to initialize preprocessor for '%s': %s", self.target_table, exc)
      return False
    except Exception as exc:
      logging.error("Failed to initialize preprocessor for '%s': %s", self.target_table, exc)
      return False

    if self.inference_mode in {"if", "hybrid"}:
      try:
        logging.info("Loading Unsupervised Model (Isolation Forest) from %s...", self.ISOLATIONFOREST_MODEL_PATH)
        self.model_if = joblib.load(self.ISOLATIONFOREST_MODEL_PATH)
      except FileNotFoundError:
        logging.error(f"Isolation Forest model not found at {self.ISOLATIONFOREST_MODEL_PATH}. Worker cannot start.")
        return False
      except Exception as e:
        logging.error(f"Failed to load Isolation Forest model: {e}")
        return False
    else:
      logging.info("Skipping Isolation Forest load because the selected mode is '%s'.", self.inference_mode)

    if self.inference_mode in {"rf", "hybrid"}:
      try:
        if self.RANDOMFOREST_MODEL_PATH and os.path.exists(self.RANDOMFOREST_MODEL_PATH):
          logging.info("Loading Supervised Model (Random Forest) from %s...", self.RANDOMFOREST_MODEL_PATH)
          self.model_rf = joblib.load(self.RANDOMFOREST_MODEL_PATH)
        else:
          if self.inference_mode == "rf":
            logging.warning("Random Forest model not found. Cannot start in '%s' mode.", self.inference_mode)
            return False

          logging.warning(
            "Random Forest model not found. Falling back to Isolation Forest mode for '%s'.",
            self.target_table,
          )
          self.inference_mode = "if"
      except Exception as e:
        logging.error(f"Failed to load Random Forest model. Error: {e}")
        if self.inference_mode == "rf":
          return False
        logging.warning("Falling back to Isolation Forest mode due to Random Forest load failure.")
        self.inference_mode = "if"
    else:
      logging.info("Skipping Random Forest load because the selected mode is '%s'.", self.inference_mode)
      
    # Record the active version so we can detect future changes
    if version_record:
        self.last_active_version = version_record["version"]
    else:
        self.last_active_version = None

    # Record current mtime for all loaded model files to detect future changes
    model_paths_to_track = [
        self.ISOLATIONFOREST_MODEL_PATH,
        self.TRANSLATOR_PATH,
        self.SCALER_PATH,
    ]
    if self.RANDOMFOREST_MODEL_PATH:
        model_paths_to_track.append(self.RANDOMFOREST_MODEL_PATH)

    for path in model_paths_to_track:
        if os.path.exists(path):
            self.last_model_files_mtime[path] = os.path.getmtime(path)

    return True
        
  def _register_pipeline(self):
    """The worker creates a registration for itself, so the anomalies hub can check its data"""
      
    engine = get_db_engine()

    create_table_query = text("""
      CREATE TABLE IF NOT EXISTS pipelines_config (
        target_table VARCHAR(100) PRIMARY KEY,
        pipeline_name VARCHAR(100),
        columns_to_ignore TEXT,
        date_columns TEXT,
        inference_mode VARCHAR(50) DEFAULT 'hybrid',
        status VARCHAR(20) DEFAULT 'active',
        last_startup TIMESTAMP
      );
    """)

    alter_table_query = text("""
      ALTER TABLE pipelines_config
      ADD COLUMN IF NOT EXISTS inference_mode VARCHAR(50) DEFAULT 'hybrid';
    """)

    cols_ignore_str = ",".join(self.columns_to_ignore) if self.columns_to_ignore else ""
    dates_str = ",".join(self.date_columns) if self.date_columns else ""
      
    nome_bonito = f"Worker de {self.target_table.replace('_', ' ').title()}"

    upsert_query = text("""
      INSERT INTO pipelines_config (target_table, pipeline_name, columns_to_ignore, date_columns, inference_mode, last_startup)
      VALUES (:target, :name, :cols, :dates, :inference_mode, CURRENT_TIMESTAMP)
      ON CONFLICT (target_table)
      DO UPDATE SET 
        columns_to_ignore = EXCLUDED.columns_to_ignore,
        date_columns = EXCLUDED.date_columns,
        inference_mode = EXCLUDED.inference_mode,
        last_startup = EXCLUDED.last_startup,
        status = 'active';
    """)

    try:
      with engine.connect() as conn:
        conn.execute(create_table_query)
        conn.execute(alter_table_query)
        conn.execute(upsert_query, {
          "target": self.target_table,
          "name": nome_bonito,
          "cols": cols_ignore_str,
          "dates": dates_str,
          "inference_mode": self.inference_mode,
        })
        conn.commit()
        logging.info(f"Pipeline {self.target_table} inserted in anomalies hub")
    except Exception as e:
      logging.error(f"Error registering the pipeline at anomalies Hub: {e}")