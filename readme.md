# Radio Show Recording Bot

This bot automatically records radio shows from a stream URL based on schedule data from the Spinitron API, uploads recordings to AWS S3, and emails links to DJs.

## Features

- Automatically fetches show schedules from Spinitron API
- Records shows using ffmpeg
- Uploads recordings to AWS S3
- Emails download links to DJs
- Includes song list data in emails
- Comprehensive error handling and logging

## Setup

1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Install ffmpeg: `sudo apt-get install ffmpeg` (Ubuntu/Debian)
4. Configure AWS CLI: `aws configure`
5. Copy `config.toml.example` to `config.toml` and edit with your settings
6. Run the bot: `python main.py`

## Configuration

Edit `config.toml` with your settings:

```toml
[email]
address = "your-email@example.com"
password = "your-app-password"

[api]
spinitron_key = "your-spinitron-api-key"

[streaming]
url = "https://your-stream-url.com/stream"

[storage]
s3_bucket = "your-s3-bucket-name"

[logging]
file = "recorder.log"
level = "INFO"
max_size = 10485760  # 10MB
backup_count = 5

[logging.loggers]
main = "INFO"
schedule = "INFO"
api = "INFO"
recorder = "INFO"
email = "INFO"
file_ops = "INFO"

[logging.filters]
show_schedule = true
show_api_calls = true
show_recording = true
show_email = true
show_file_ops = true
```

## Usage

Start the bot with:

```bash
python main.py
```

It will automatically:
1. Fetch the schedule from Spinitron
2. Schedule recordings for upcoming shows
3. Record shows when they start
4. Upload recordings to S3
5. Email download links to DJs

## Troubleshooting

Check the log file (default: `recorder.log`) for detailed information about any issues.

Common problems:
- Incorrect Spinitron API key - check your API key in config.toml
- Missing ffmpeg - ensure ffmpeg is installed
- AWS S3 permissions - verify your AWS credentials and bucket permissions
- Email sending failures - check your email address and app password