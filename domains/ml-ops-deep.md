# VIGIL Domain Detail: ML Operations Deep-Dive

**Parent cluster:** backend
**Loaded in:** siege mode, or --only backend --deep

## Deep Checks

### Model Versioning

```bash
# check for model version tracking
grep -rn "model_version\|MODEL_VERSION\|model_name\|model_id" src/ --include="*.py" --include="*.ts" | grep -v "//\|#\|test" | head -20

# MLflow model registry
grep -rn "mlflow\|MlflowClient\|register_model\|log_model" src/ --include="*.py" | head -20
mlflow models list 2>/dev/null | head -20

# HuggingFace model hub pinning (revision= or commit hash)
grep -rn "from_pretrained\|hf_hub_download" src/ --include="*.py" | grep -v "revision=\|commit_hash\|sha256" | head -10

# model file checksums
find . -name "*.pt" -o -name "*.safetensors" -o -name "*.onnx" -o -name "*.pkl" | xargs sha256sum 2>/dev/null | head -20

# hardcoded model paths vs config-driven
grep -rn "\.pt\"\|\.bin\"\|\.onnx\"\|\.pkl\"" src/ --include="*.py" | grep -v "config\|env\|os\.environ" | head -10
```

### Experiment Tracking

```bash
# MLflow / Weights & Biases / Neptune usage
grep -rn "import mlflow\|import wandb\|import neptune\|from comet_ml\|from clearml" src/ --include="*.py" | head -10

# experiment parameters logged
grep -rn "log_param\|log_metric\|log_artifact\|wandb\.log\|run\.log" src/ --include="*.py" | head -20

# random seeds set for reproducibility
grep -rn "random\.seed\|np\.random\.seed\|torch\.manual_seed\|tf\.random\.set_seed\|set_seed" src/ --include="*.py" | head -10

# missing experiment run naming
grep -rn "mlflow\.start_run\|wandb\.init\|neptune\.init_run" src/ --include="*.py" | grep -v "name=\|run_name=\|tags=" | head -10
```

### Data Versioning (DVC)

```bash
# DVC setup check
ls -la .dvc/ 2>/dev/null
cat .dvc/config 2>/dev/null
dvc status 2>/dev/null | head -20

# tracked large files
dvc list . --recursive 2>/dev/null | head -20
find . -name "*.dvc" | head -20

# data pipeline stages
dvc dag 2>/dev/null

# raw data not under version control
find data/ -name "*.csv" -o -name "*.parquet" -o -name "*.jsonl" 2>/dev/null | xargs ls -lh | sort -k5 -hr | head -20

# check .gitignore for large data files
grep -n "\.csv\|\.parquet\|\.h5\|\.tfrecord\|\.npy\|\.npz" .gitignore 2>/dev/null
```

### Feature Store Patterns

```bash
# feature store usage (Feast, Tecton, Hopsworks, Redis)
grep -rn "FeatureStore\|feast\|tecton\|hopsworks\|feature_view\|get_online_features" src/ --include="*.py" | head -20

# feature computation in serving path (should be precomputed)
grep -rn "def.*feature\|compute_feature\|engineer_feature" src/ --include="*.py" | head -20

# feature drift between training and serving
grep -rn "training_data\|train_df\|X_train\|offline.*feature" src/ --include="*.py" | head -20

# feature schema validation
grep -rn "FeatureSchema\|feature_dtype\|validate_features\|great_expectations\|pandera" src/ --include="*.py" | head -10
```

### Model Serving

```bash
# latency targets and SLOs defined
grep -rn "timeout\|SLO\|latency_ms\|max_latency\|response_time" src/ --include="*.py" --include="*.ts" | grep -i "model\|predict\|infer" | head -10

# batch inference vs real-time
grep -rn "\.predict_batch\|batch_size\|DataLoader\|batch_predict" src/ --include="*.py" | head -20

# model loaded per request vs cached singleton
grep -rn "load_model\|from_pretrained\|torch\.load\|tf\.saved_model\.load" src/ --include="*.py" | head -20
grep -rn "@lru_cache\|@cache\|_model_cache\|_singleton\|MODEL_CACHE" src/ --include="*.py") | grep -i "model\|pipeline" | head -10

# ONNX / TorchScript optimization
grep -rn "onnxruntime\|torch\.jit\|torch\.compile\|torch\.quantization\|bitsandbytes" src/ --include="*.py" | head -10

# GPU memory management
grep -rn "cuda()\|\.to('cuda')\|device_map\|gpu_memory_fraction" src/ --include="*.py" | head -10
grep -rn "torch\.cuda\.empty_cache\|gc\.collect" src/ --include="*.py") | wc -l
```

### A/B Testing Infrastructure

```bash
# traffic splitting / shadow mode
grep -rn "canary\|shadow\|a_b_test\|experiment\|variant\|split_traffic\|rollout" src/ --include="*.py" --include="*.ts" | head -20

# feature flags for model variants
grep -rn "feature_flag\|LaunchDarkly\|Split\|Unleash\|flagsmith" src/ --include="*.py" --include="*.ts" | head -10

# logging predictions for offline evaluation
grep -rn "log_prediction\|prediction_log\|feedback\|ground_truth\|label_store" src/ --include="*.py" | head -10

# statistical significance testing
grep -rn "statsmodels\|scipy\.stats\|t_test\|chi2\|mann_whitney\|p_value" src/ --include="*.py") | grep -i "experiment\|ab_test\|significance" | head -10
```

### Model Monitoring

```bash
# drift detection setup
grep -rn "evidently\|alibi-detect\|seldon\|nannyml\|deepchecks\|whylogs\|arize" src/ --include="*.py" | head -10

# prediction distribution monitoring
grep -rn "monitor\|alert\|drift\|distribution\|baseline_stats" src/ --include="*.py" --include="*.ts" | grep -i "model\|predict\|infer" | head -20

# performance metric logging
grep -rn "accuracy\|precision\|recall\|f1\|auc\|rmse\|mae\|mse" src/ --include="*.py") | grep -v "test\|eval\|train\|compute_" | head -20

# stale model detection (serving old version)
grep -rn "model_created_at\|model_timestamp\|model_freshness\|max_model_age" src/ --include="*.py" | head -10

# alerting on prediction anomalies
grep -rn "pagerduty\|opsgenie\|slack.*alert\|send_alert\|notify" src/ --include="*.py") | grep -i "model\|drift\|anomaly" | head -10
```

### Reproducibility

```bash
# environment pinning
cat requirements.txt 2>/dev/null | grep -E "^[a-zA-Z].*==" | wc -l
cat requirements.txt 2>/dev/null | grep -v "==" | grep -v "^#\|^$" | head -10

# Docker base image pinning (digest vs tag)
grep -rn "FROM " Dockerfile* | grep -v "@sha256" | head -10

# non-deterministic operations
grep -rn "dropout\|Dropout\|stochastic\|random\|augment" src/ --include="*.py" | grep -v "seed\|deterministic\|eval()" | head -20

# training script CLI arguments logged
grep -rn "argparse\|typer\|click\|fire\|hydra" src/ --include="*.py") | head -10
grep -rn "log_param\|mlflow\.log\|wandb\.config" src/ --include="*.py") | wc -l
```

## Advanced Patterns

| Pattern | Severity | Category |
|---------|----------|----------|
| Model loaded from unpinned `latest` tag | High | Reproducibility / silent regressions |
| No experiment tracking on training runs | Medium | Irreproducibility |
| Feature engineering in prediction path (not training) | High | Training/serving skew |
| No data validation before training | High | Garbage-in model |
| A/B test without statistical power analysis | Medium | Invalid conclusions |
| Model file in Git LFS without DVC pipeline | Medium | No lineage to training data |
| Missing `eval()` mode in PyTorch inference | High | Wrong predictions (dropout active) |
| Batch size tuned for accuracy, not latency | Medium | SLO violation in production |
| No rollback strategy for model updates | High | Irreversible degradation |
| PII in training data without anonymization | Critical | Privacy / GDPR |
| No model card / documentation for deployed model | Medium | Governance gap |
