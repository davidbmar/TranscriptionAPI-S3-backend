import os
#!/usr/bin/python3
import uuid
import json
from functools import wraps
from flask import Flask, request, jsonify, abort
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables from .env file (optional, useful for local dev)
load_dotenv()

app = Flask(__name__)

# --- Configuration ---
# Fetch S3 bucket name from environment variable or use a default
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "2025-04-18-audio-transcription-api-s3-backend-us-east-2")
# Fetch AWS region from environment variable or use a default
AWS_REGION = os.environ.get("AWS_REGION", "us-east-2")
# Presigned URL expiration time in seconds (e.g., 15 minutes)
PRESIGNED_URL_EXPIRATION = int(os.environ.get("PRESIGNED_URL_EXPIRATION", 900))

# --- Determine the correct S3 endpoint URL based on the region ---
# Standard regional endpoint format
s3_endpoint_url = f'https://s3.{AWS_REGION}.amazonaws.com'
# Handle potential edge case for us-east-1 which sometimes doesn't need the region in the URL
# Although for consistency, including it is generally fine. Boto3 might handle this,
# but being explicit might help here. If us-east-1 was the region, you might use:
# s3_endpoint_url = 'https://s3.amazonaws.com' if AWS_REGION == 'us-east-1' else f'https://s3.{AWS_REGION}.amazonaws.com'

print ("this is the bucket :"+S3_BUCKET_NAME)
print ("this is the region :"+AWS_REGION)
print ("this is the endpoint URL:"+s3_endpoint_url) # Added print for endpoint

# --- Mock API Key Storage (Replace with a secure database/secrets manager) ---
# In a real application, fetch these securely, e.g., from AWS Secrets Manager or a database.
# Format: { "api_key": "username" }
API_KEYS = {
    os.environ.get("USER1_API_KEY", "test_key_user1_abc"): "user1",
    os.environ.get("USER2_API_KEY", "test_key_user2_def"): "user2",
    # Add more keys as needed
    # Make sure the key you use in testing actually exists here or in env vars
    os.environ.get("SECURE_USER1_KEY", "your_secure_api_key_for_user1"): "user1",
}

# --- AWS S3 Client ---
# Explicitly provide the endpoint_url based on the region
s3_client = boto3.client(
    's3',
    region_name=AWS_REGION,
    endpoint_url=s3_endpoint_url, # *** ADDED THIS LINE ***
    # Credentials will be automatically picked up from standard locations:
    # 1. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN)
    # 2. Shared credential file (~/.aws/credentials)
    # 3. AWS config file (~/.aws/config)
    # 4. EC2 instance profile or ECS task role
    config=boto3.session.Config(signature_version='s3v4') # Recommended for presigned URLs
)

# --- Authentication Decorator ---
def require_api_key(f):
    """Decorator to enforce API key authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('Authorization')
        if not api_key or not api_key.startswith('Bearer '):
            abort(401, description="Authorization header missing or invalid (Bearer token required).")

        token = api_key.split('Bearer ')[1]
        username = API_KEYS.get(token)

        if not username:
            # Add extra logging to see which key failed
            print(f"Failed auth attempt with token: {token[:5]}...") # Log prefix only
            abort(401, description="Invalid API Key.")

        # Store username for potential use in the route function
        request.authenticated_username = username
        return f(*args, **kwargs)
    return decorated_function

# --- Helper Functions ---
def validate_username(provided_username):
    """Ensure the provided username matches the authenticated user."""
    authenticated_username = getattr(request, 'authenticated_username', None)
    if not authenticated_username or provided_username != authenticated_username:
         abort(403, description="Provided username does not match authenticated API key.")


# --- API Endpoints ---

@app.route('/v1/uploads/presigned-url', methods=['POST'])
@require_api_key
def generate_presigned_url():
    """
    Generates a presigned URL for uploading a single audio file.
    Authenticates using Bearer token and derives username from the token.
    """
    username = getattr(request, 'authenticated_username', None)
    if not username:
         # Should not happen if require_api_key works, but added for safety
         abort(401, description="Authentication failed.")

    transcription_id = str(uuid.uuid4())
    s3_object_key = f"uploads/{username}/{transcription_id}/audio.mp3"

    try:
        print(f"Generating URL for Bucket: {S3_BUCKET_NAME}, Key: {s3_object_key}, Region: {AWS_REGION}, Endpoint: {s3_endpoint_url}")
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': S3_BUCKET_NAME,
                'Key': s3_object_key,
                # Optional: Add content type restriction if needed
                # 'ContentType': 'audio/mpeg'
                },
            ExpiresIn=PRESIGNED_URL_EXPIRATION,
            HttpMethod='PUT'
        )
        print(f"Generated URL: {presigned_url}") # Log the generated URL
        return jsonify({
            "presigned_url": presigned_url,
            "transcription_id": transcription_id
        }), 200
    except ClientError as e:
        print(f"Error generating presigned URL: {e}")
        # Log more details if possible
        print(f"Boto3 client config: region={s3_client.meta.region_name}, endpoint={s3_client.meta.endpoint_url}")
        abort(500, description="Could not generate presigned URL.")
    except Exception as e:
        print(f"Unexpected error: {e}")
        abort(500, description="An unexpected server error occurred.")


@app.route('/v1/uploads/validate', methods=['GET'])
@require_api_key
def validate_upload():
    """
    Validates if an audio file exists in S3 for a given transcription_id.
    Requires username and transcription_id as query parameters.
    Validates that the provided username matches the authenticated user.
    """
    username = request.args.get('username')
    transcription_id = request.args.get('transcription_id')

    if not username or not transcription_id:
        abort(400, description="Missing required query parameters: username, transcription_id.")

    # Security check: Ensure the requested username matches the token's user
    validate_username(username)

    s3_object_key = f"uploads/{username}/{transcription_id}/audio.mp3"

    try:
        # head_object is efficient for checking existence and getting metadata
        print(f"Validating upload for Bucket: {S3_BUCKET_NAME}, Key: {s3_object_key}")
        response = s3_client.head_object(Bucket=S3_BUCKET_NAME, Key=s3_object_key)
        file_size_bytes = response.get('ContentLength', 0)
        # Simple conversion to MB for display
        file_size_mb = f"{file_size_bytes / (1024 * 1024):.2f}MB" if file_size_bytes else "0MB"

        return jsonify({
            "transcription_id": transcription_id,
            "status": "uploaded",
            "file_size": file_size_mb,
            "s3_key": s3_object_key # Optional: return the key for debugging
        }), 200

    except ClientError as e:
        if e.response['Error']['Code'] == '404' or e.response['Error']['Code'] == 'NoSuchKey':
             # Standard way S3 indicates object not found
            print(f"Validation: Object not found - {s3_object_key}")
            return jsonify({
                "transcription_id": transcription_id,
                "status": "not_found",
                "file_size": None,
                "s3_key": s3_object_key
            }), 404
        else:
            # Handle other potential S3 errors (permissions, etc.)
            print(f"Error validating upload: {e}")
            abort(500, description=f"Error checking S3 object: {e.response['Error']['Message']}")
    except Exception as e:
        print(f"Unexpected error during validation: {e}")
        abort(500, description="An unexpected server error occurred during validation.")


@app.route('/v1/transcriptions/<string:transcription_id>', methods=['GET'])
@require_api_key
def get_transcription(transcription_id):
    """
    Retrieves the transcription result from S3.
    Derives username from the authenticated API key.
    NOTE: This assumes the transcription process (external to this API)
          has completed and placed the transcript.json file in the correct S3 location.
    """
    username = getattr(request, 'authenticated_username', None)
    if not username:
         abort(401, description="Authentication failed.") # Should be caught by decorator

    s3_object_key = f"transcriptions/{username}/{transcription_id}/transcript.json"

    try:
        print(f"Getting transcription for Bucket: {S3_BUCKET_NAME}, Key: {s3_object_key}")
        response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=s3_object_key)
        # Read the content of the file
        transcription_content = response['Body'].read().decode('utf-8')
        # Parse the JSON content
        transcription_data = json.loads(transcription_content)

        # Return the entire content of the JSON file
        return jsonify(transcription_data), 200

    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            # If the transcript file doesn't exist yet
            print(f"Transcription not found: {s3_object_key}")
            return jsonify({
                "transcription_id": transcription_id,
                "status": "processing or not found",
                "message": "Transcription result not available yet or does not exist.",
                "s3_key": s3_object_key
            }), 404 # Not Found is appropriate here
        else:
            # Handle other S3 errors
            print(f"Error retrieving transcription: {e}")
            abort(500, description=f"Error retrieving transcription from S3: {e.response['Error']['Message']}")
    except json.JSONDecodeError:
         print(f"Error decoding JSON from S3 key: {s3_object_key}")
         abort(500, description="Transcription file found but contains invalid JSON.")
    except Exception as e:
        print(f"Unexpected error retrieving transcription: {e}")
        abort(500, description="An unexpected server error occurred while retrieving transcription.")


# --- Root/Health Check Endpoint ---
@app.route('/')
def health_check():
    """Basic health check endpoint."""
    return jsonify({"status": "ok", "message": "Audio Transcription API is running."}), 200

# --- Error Handlers ---
@app.errorhandler(400)
def bad_request(error):
    return jsonify(error=str(error.description)), 400

@app.errorhandler(401)
def unauthorized(error):
    return jsonify(error=str(error.description)), 401

@app.errorhandler(403)
def forbidden(error):
    return jsonify(error=str(error.description)), 403

@app.errorhandler(404)
def not_found(error):
     # Check if it's our custom JSON response or a standard Flask 404
    if isinstance(error.description, dict):
        return jsonify(error.description), 404
    return jsonify(error=str(error.description) if error.description else "Resource not found."), 404

@app.errorhandler(500)
def internal_server_error(error):
    return jsonify(error=str(error.description) if error.description else "Internal Server Error"), 500


# --- Main Execution ---
if __name__ == '__main__':
    # Set debug=True for development, but turn off for production
    # Use host='0.0.0.0' to make it accessible on your network (e.g., from EC2)
    # Consider removing debug=True when running behind Apache/Gunicorn
    app.run(host='0.0.0.0', port=5000, debug=True)

