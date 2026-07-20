# Model directory

Place the trained road-damage checkpoint at `models/best.pt`, or set
`ROADWATCH_MODEL_PATH` to another location. Model weights are intentionally excluded from
Git because they are large binary artifacts and must have independently documented training
data, evaluation results, and provenance.

The API remains live but reports **not ready** when a checkpoint is missing. It never silently
substitutes an unrelated generic object detector.

