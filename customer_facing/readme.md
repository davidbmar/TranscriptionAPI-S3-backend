# Developer Guide: Audio Upload API via Command Line

## Overview

This document serves as a user-facing guide for developers to interact with the audio upload API using command-line tools. It is intended for customers or clients who want to programmatically upload audio files and retrieve transcriptions.

---

## Use Cases

| Use Case                             | Description                                                         |
| ------------------------------------ | ------------------------------------------------------------------- |
| Upload a single audio file           | Upload a single file via a presigned URL from the CLI.              |
| Upload multiple files (batch upload) | Request multiple presigned URLs and upload audio files in parallel. |
| Validate an uploaded file            | Confirm that an audio file was uploaded successfully to S3.         |
| Retrieve transcription result        | Download the transcription file once processing is complete.        |
| Monitor upload activity              | Optional functionality to list or audit uploads for transparency.   |

---

## Authentication

All API requests require a Bearer token:

```bash
-H "Authorization: Bearer YOUR_API_KEY"
```

You must also provide your username as a query parameter when requesting a presigned URL.

---

## Step-by-Step Guide

### 1. Request a Presigned Upload URL

Send a POST request to get a presigned URL:

```bash
curl -X POST "https://api.example.com/v1/uploads/presigned-url?username=user123" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

Expected response:

```json
{
  "presigned_url": "https://s3.amazonaws.com/your-bucket/uploads/user123/{transcription_id}/audio.mp3?...",
  "transcription_id": "{transcription_id}"
}
```

---

### 2. Upload the Audio File to S3

Use the provided `presigned_url` to upload your audio file directly:

```bash
curl -X PUT "PRESIGNED_URL" \
  -H "Content-Type: audio/mpeg" \
  --upload-file path/to/audio.mp3
```

---

### 3. (Optional) Upload Multiple Files

Request multiple presigned URLs:

```bash
curl -X POST "https://api.example.com/v1/uploads/presigned-urls?username=user123" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{"file_count": 5}'
```

Upload each file with its corresponding presigned URL.

---

### 4. Validate Upload Completion

To check if an upload was successful:

```bash
curl -X GET "https://api.example.com/v1/uploads/validate?username=user123&transcription_id={transcription_id}" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

Example response:

```json
{
  "transcription_id": "{transcription_id}",
  "status": "uploaded",
  "file_size": "2MB"
}
```

---

### 5. Retrieve Transcription

Once processing completes, you can download your transcription:

```bash
curl -X GET "https://api.example.com/v1/transcriptions/{transcription_id}" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

## Optional Features (Coming Soon)

| Feature              | Purpose                                                 |
| -------------------- | ------------------------------------------------------- |
| Attach metadata      | Add custom fields (e.g., language, tags, speaker info). |
| Webhook notification | Receive a callback when transcription is complete.      |
| Audit log access     | Review history of uploads and downloads.                |
| Manual trigger       | Trigger transcription manually instead of auto-start.   |
| API key rotation     | Regenerate or revoke API keys securely.                 |

---

## Contact & Support

If you encounter issues or need support:

- Visit our documentation site
- Contact our support team at support\@example.com

---

This page is intended to help developers get started quickly and confidently. For implementation details or server-side architecture, please refer to the internal design document.


