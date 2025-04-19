# Internal Design Spec: Audio Upload and Transcription API

## Objective

This document outlines what should be implemented based on the high-level design for a secure, command-line-accessible transcription API that uses AWS S3 and presigned URLs. This spec will serve as a guide to begin implementation.

---

## Core Features to Implement (MVP)

### 1. **Generate Presigned URL for Single File Upload**
**Endpoint:** `POST /v1/uploads/presigned-url`

**Inputs:**
- `Authorization: Bearer API_KEY` (in header)
- `username` (query param)

**Logic:**
- Authenticate API key and match to user
- Generate `transcription_id` (UUID)
- Return a presigned `PUT` URL to upload audio file to:
  ```
  uploads/{username}/{transcription_id}/audio.mp3
  ```

**Outputs:**
```json
{
  "presigned_url": "https://...",
  "transcription_id": "uuid"
}
```

---

### 2. **Upload Audio File to Presigned URL (via CLI)**
- No backend work needed (user uses `curl` with returned URL)

---

### 3. **Validate Upload**
**Endpoint:** `GET /v1/uploads/validate`

**Inputs:**
- `Authorization: Bearer API_KEY`
- `username`, `transcription_id`

**Logic:**
- Check if the file exists in S3 at `uploads/{username}/{transcription_id}/audio.mp3`
- Return file size and status

**Output:**
```json
{
  "transcription_id": "...",
  "status": "uploaded",
  "file_size": "2MB"
}
```

---

### 4. **Retrieve Transcription Result**
**Endpoint:** `GET /v1/transcriptions/{transcription_id}`

**Inputs:**
- `Authorization: Bearer API_KEY`
- `username` (from token or query param)

**Logic:**
- Look up in S3 at `transcriptions/{username}/{transcription_id}/transcript.json`
- Return contents of transcription

**Output:**
```json
{
  "transcription": "..."
}
```

---

## Optional/Next Features

| Feature                     | Description                                                    |
|----------------------------|----------------------------------------------------------------|
| Batch Presigned URLs       | Allow requesting 1-N presigned URLs in one call                |
| Attach Metadata            | JSON with hints like language, tags, speaker names             |
| Webhook on Completion      | Notify client webhook URL when transcription is ready          |
| Manual Transcription Start | Explicit start command, instead of S3 event trigger            |
| Audit Log Access           | List of uploads, timestamps, and retrievals per user           |
| API Key Management         | Rotate/revoke keys via API                                     |

---

## Key S3 Structure

```
/your-audio-bucket/
├── uploads/
│   └── {username}/
│       └── {transcription_id}/audio.mp3
└── transcriptions/
    └── {username}/
        └── {transcription_id}/transcript.json
```

---

## Security Measures

- Use Bearer token for all requests
- Validate token matches the username in path/query
- Expire presigned URLs after 5–15 minutes
- Use IAM roles to enforce S3 prefix-per-user access policy if needed

---

## Implementation Order

1. Token validation + presigned URL generation (Lambda or Node.js/Flask)
2. Upload validation endpoint
3. Transcription fetch endpoint
4. S3 bucket setup and lifecycle policy (optional)
5. Logging + Error handling

---

Ready to implement? Start by writing the presigned URL handler. All logic should be modular to allow serverless or container deployment. Ask if you'd like code scaffolding.


