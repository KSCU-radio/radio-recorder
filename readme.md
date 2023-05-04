# Radio Show Recorder

This program is an automated radio show recorder that records shows from a streaming URL, uploads the recorded shows to an Amazon S3 bucket, and sends an email to the DJs with a download link to their recorded show. It schedules recordings for the upcoming 24 shows using the Spinitron API.

The program is intended to run on an AWS EC2 Instance and upload files to an Amazon S3 bucket. It can be run on a local machine, but the AWS CLI must be configured and the AWS credentials must have permission to upload files to the S3 bucket.

Originally developed for [KSCU 103.3 FM](https://www.kscu.org/), the student-run radio station at Santa Clara University. Check us out!

## Features

- Automatically records radio shows from a streaming URL
- Uploads recorded shows to an Amazon S3 bucket
- Sends an email to DJs with a link to download their recorded show
- Schedules recordings for the next 24 shows using the Spinitron API
- Ignores shows that are tagged with the 'automation' category.

## Requirements

- Python 3.x
- [FFmpeg](https://www.ffmpeg.org/download.html)
- [AWS CLI](https://aws.amazon.com/cli/)
- A Spinitron API key
- DJ emails listed as 'public emails' on Spinitron
- A Gmail account for sending emails
- An Amazon S3 bucket for storing the recorded shows

## Installation

1. Clone the repository:
```
git clone https://github.com/yourusername/radio-show-recorder.git
cd radio-show-recorder
```

2. Install the required Python libraries:
```
pip install -r requirements.txt
```

3. Set up the environment variables in a `.env` file:
```
API_KEY=your_spinitron_api_key
EMAIL=your_gmail_email
PASSWORD=your_gmail_password
```

4. Make sure that FFmpeg and the AWS CLI are installed and configured on your system.

## Usage

To run the program, simply execute the script:

```
python radio_show_recorder.py
```

The script will run indefinitely, continuously updating the recording schedule and processing new shows.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request if you have any improvements or suggestions.
