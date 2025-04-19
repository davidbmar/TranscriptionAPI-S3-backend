# Audio Transcription API - Setup Guide

## Overview

This guide outlines the steps to set up and run the Python Flask-based Audio Transcription API on an AWS EC2 instance behind an Apache reverse proxy. The API allows generating presigned S3 URLs for audio uploads, validating uploads, and retrieving (mock) transcription results.

## Prerequisites

* An AWS EC2 instance (Ubuntu/Amazon Linux recommended).
* SSH access to the EC2 instance.
* Python 3 and `pip` installed on the instance.
* Apache2 web server installed (`sudo apt update && sudo apt install apache2` or `sudo yum update && sudo yum install httpd`).
* `mod_proxy`, `mod_proxy_http`, `mod_ssl`, `mod_rewrite` enabled in Apache.
* An SSL certificate (e.g., from Let's Encrypt) configured for your domain in Apache.
* An AWS Account.
* An S3 bucket created in a specific AWS region.
* An IAM Role attached to the EC2 instance with permissions for:
    * `s3:PutObject` (for the upload path, e.g., `arn:aws:s3:::your-bucket-name/uploads/*`)
    * `s3:HeadObject` (for the upload path)
    * `s3:GetObject` (for the transcription path, e.g., `arn:aws:s3:::your-bucket-name/transcriptions/*`)

## Setup Steps

1.  **Get Code:**
    * Clone your Git repository or use `scp` to copy the `AudioTranscriptionAPI.py` script and `requirements.txt` file to your EC2 instance (e.g., into `~/working/TranscriptionAPI-S3-backend/src`).

2.  **Install Dependencies:**
    * Navigate to the source directory (`cd ~/working/TranscriptionAPI-S3-backend/src`).
    * Install required Python packages:
        ```bash
        python3 -m pip install -r requirements.txt
        ```

3.  **Configure Environment Variables:**
    * These variables are needed by the `AudioTranscriptionAPI.py` script. Set them in the environment where the application process will run (e.g., export in the shell before running `nohup`, or add to a systemd service file).
    * **Crucially, ensure the application process is restarted after setting/changing these.**
        ```bash
        # Replace with your actual bucket name
        export S3_BUCKET_NAME="your-actual-s3-bucket-name"

        # Replace with the ACTUAL region your S3 bucket is in (e.g., us-east-2)
        export AWS_REGION="us-east-2"

        # Set your secure API keys (Consider using AWS Secrets Manager in production)
        export USER1_API_KEY="your_secure_api_key_for_user1"
        export USER2_API_KEY="your_secure_api_key_for_user2"
        # Add any other keys defined in the API_KEYS dictionary in the script

        # Optional: Set presigned URL expiry time in seconds
        # export PRESIGNED_URL_EXPIRATION="900" # 15 minutes
        ```
    * **Note:** Using an IAM Role (Prerequisite #5) is the recommended way to handle AWS credentials instead of setting access keys as environment variables.

4.  **Configure Apache Reverse Proxy:**
    * Edit your Apache site configuration file (e.g., `/etc/apache2/sites-available/your-site.conf` or `/etc/httpd/conf.d/your-site.conf`).
    * Ensure you have a `<VirtualHost *:443>` block configured for SSL.
    * Add `ProxyPass` directives to forward requests to your backend application (running on port 5000 in this example). Make sure the path matches your application's routes.
    * **Example Snippet (within `<VirtualHost *:443>`):**
        ```apache
        <IfModule mod_ssl.c>
        <VirtualHost *:443>
            ServerName yourdomain.com
            ServerAlias [www.yourdomain.com](https://www.yourdomain.com)
            DocumentRoot /var/www/html # Or your relevant root

            # SSL Configuration (Let's Encrypt example)
            SSLEngine on
            SSLCertificateFile /etc/letsencrypt/live/[yourdomain.com/fullchain.pem](https://yourdomain.com/fullchain.pem)
            SSLCertificateKeyFile /etc/letsencrypt/live/[yourdomain.com/privkey.pem](https://yourdomain.com/privkey.pem)
            Include /etc/letsencrypt/options-ssl-apache.conf

            # Set headers for backend app
            RequestHeader set X-Forwarded-Proto "https"
            RequestHeader set X-Forwarded-Port "443"
            ProxyPreserveHost On # Important for Flask to see the original host

            # Proxy requests to the Flask app running on port 5000
            # Ensure this comes *after* any more specific ProxyPass rules if needed
            ProxyPass / http://localhost:5000/
            ProxyPassReverse / http://localhost:5000/

            ErrorLog ${APACHE_LOG_DIR}/error.log
            CustomLog ${APACHE_LOG_DIR}/access.log combined
        </VirtualHost>
        </IfModule>

        # Optional: Redirect HTTP to HTTPS
        <VirtualHost *:80>
            ServerName yourdomain.com
            ServerAlias [www.yourdomain.com](https://www.yourdomain.com)
            Redirect permanent / [https://yourdomain.com/](https://yourdomain.com/)
        </VirtualHost>
        ```
    * Enable necessary Apache modules: `sudo a2enmod proxy proxy_http ssl rewrite headers` (Debian/Ubuntu) or ensure they are loaded in httpd.conf.
    * Restart Apache: `sudo systemctl restart apache2` (or `sudo systemctl restart httpd`).

## Running the Application

1.  **Development (Not Recommended for Production):**
    * Navigate to the source directory.
    * Ensure environment variables are set (`export ...`).
    * Run directly with Python:
        ```bash
        python3 AudioTranscriptionAPI.py
        ```
    * This uses the built-in Flask development server, which is not efficient or robust for handling traffic.

2.  **Production (Gunicorn Recommended):**
    * Install Gunicorn: `python3 -m pip install gunicorn`
    * Navigate to the source directory.
    * Run using Gunicorn, binding to localhost (Apache will handle external traffic):
        ```bash
        # Run in the foreground (for testing or if managed by systemd)
        gunicorn --workers 3 --bind 127.0.0.1:5000 AudioTranscriptionAPI:app

        # Run in the background using nohup (simpler, less robust)
        nohup gunicorn --workers 3 --bind 127.0.0.1:5000 AudioTranscriptionAPI:app &
        ```
        * `AudioTranscriptionAPI:app` refers to the filename `AudioTranscriptionAPI.py` and the Flask instance named `app` inside it. Adjust if needed.
        * `--workers 3`: Adjust the number of worker processes based on your EC2 instance resources.
    * **Best Practice:** Configure Gunicorn to run as a `systemd` service for better process management, logging, and automatic restarts.

## Testing the API

Use `curl` or an API client like Postman. Replace placeholders like `<yourdomain.com>`, `<your_api_key>`, `<transcription_id>`, and `<username>` accordingly.

1.  **Health Check:**
    ```bash
    curl https://<yourdomain.com>/
    ```
    *Expected Output: `{"status": "ok", "message": "Audio Transcription API is running."}`*

2.  **Get Presigned URL:**
    ```bash
    curl -X POST https://<yourdomain.com>/v1/uploads/presigned-url \
         -H "Authorization: Bearer <your_api_key>"
    ```
    *Expected Output: JSON with `presigned_url` and `transcription_id`.*

3.  **Upload File:** (Use the URL from step 2)
    ```bash
    curl -X PUT --upload-file /path/to/local/audio.mp3 "<presigned_url>"
    ```
    *Expected Output: No output on success.*

4.  **Validate Upload:** (Use the `transcription_id` from step 2)
    ```bash
    curl "https://<yourdomain.com>/v1/uploads/validate?username=<username>&transcription_id=<transcription_id>" \
         -H "Authorization: Bearer <your_api_key>"
    ```
    *Expected Output: JSON with `status: "uploaded"` and `file_size`.*

5.  **Get Transcription:** (Requires a separate process to create the transcript file)
    ```bash
    curl "https://<yourdomain.com>/v1/transcriptions/<transcription_id>" \
         -H "Authorization: Bearer <your_api_key>"
    ```
    *Expected Output: JSON content of the transcript file, or a 404 if not found.*

## Troubleshooting Common Issues

* **Connection Refused/Timeout:** Check EC2 Security Groups allow traffic on port 443 (HTTPS). Ensure Apache is running. Ensure Gunicorn/Flask is running and bound correctly (`127.0.0.1:5000`). Check Apache proxy configuration.
* **405 Method Not Allowed:** You used the wrong HTTP method for the endpoint (e.g., GET instead of POST for `/v1/uploads/presigned-url`). Use `curl -X POST` or similar.
* **401 "Authorization header missing or invalid (Bearer token required)":** The `Authorization` header is missing, or it doesn't start with `Bearer ` (note the space). Correct format: `Authorization: Bearer your_key`.
* **401 "Invalid API Key":** The key provided after `Bearer ` exists but is not found in the `API_KEYS` dictionary in the running Flask app. Check:
    * Typos in the key sent by the client.
    * The value of the corresponding environment variable (e.g., `USER1_API_KEY`) on the EC2 instance in the *environment where Gunicorn/Flask is running*.
    * Ensure the Flask/Gunicorn process was restarted after setting/changing environment variables.
* **S3 `TemporaryRedirect` Error during Upload:** The region configured in the Flask app (`AWS_REGION` env var or code default) does not match the actual region of the S3 bucket.
    * **Fix:**
        1.  Set the `AWS_REGION` environment variable correctly on the EC2 instance (e.g., `export AWS_REGION="us-east-2"`).
        2.  **Restart the Flask/Gunicorn application** to load the new region setting.
        3.  Generate a **new** presigned URL (the old one is invalid).
        4.  Retry the upload with the **new** URL.
    * **If persists:** Ensure the `boto3.client` initialization in the Flask code explicitly includes `endpoint_url=f'https://s3.{AWS_REGION}.amazonaws.com'` (as done in `audio_transcription_api_flask_v2`) and restart the app again.

## Future Considerations

* **Production Deployment:** Use Gunicorn managed by `systemd`. Implement proper logging. Secure API keys using AWS Secrets Manager.
* **Lambda Transition:** Refactor the Flask app using a framework like AWS Chalice or Zappa for easier deployment to API Gateway and Lambda. The core logic remains similar, but event handling and deployment differ significantly.
* **Actual Transcription:** Implement the transcription logic (e.g., using AWS Transcribe triggered by S3 events or called explicitly) to create the `transcript.json` file.


