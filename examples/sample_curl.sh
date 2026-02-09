curl -X POST http://127.0.0.1:8000/v1/save/assessments \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer change-me" \
  -d @examples/sample_assessment_payload.json
