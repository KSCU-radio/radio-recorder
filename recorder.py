from datetime import date, datetime, timezone, timedelta # https://docs.python.org/3/library/datetime.html
import ffmpeg # https://kkroening.github.io/ffmpeg-python/
import sched, time # https://pythontic.com/concurrency/scheduler/introduction
import os
from dateutil import parser
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('API_KEY')
EMAIL = os.getenv('EMAIL')
PASSWORD = os.getenv('PASSWORD')
print(f"https://spinitron.com/api/shows?access-token={API_KEY}&count=15")

# ffmpeg location needs to be updated depending on system
#ffmpeg = '/opt/homebrew/bin/ffmpeg' # for macOS
ffmpeg = '/usr/bin/ffmpeg' # for EC2

def getTodaysShows():
	stationData = requests.get(f"https://spinitron.com/api/shows?access-token={API_KEY}&count=15")

	# Check for a successful request
	if stationData.status_code != 200:
		print(stationData.status_code)
	stationData = stationData.json()

	# Structure of dailyRecordingSchedule = [
	# 	{
	# 		'showName': 'Name-of-Show-1'
	# 		'showStart' : datetime,
	# 		'showEnd': datetime,
	# 		'duration': int
	# 	},
	# 	{
	# 		'showName': 'Name-of-Show-2'
	# 		'showStart' : datetime,
	# 		'showEnd': datetime,
	# 		'duration': int
	# 	},
	# ]
	# 
	# Time will take into consideration Daylight Savings

	todaysRecordingSchedule = []

	for i in range(len(stationData['items'])):
		showName = "-".join(stationData['items'][i]['title'].split())
		showStart = parser.parse(stationData['items'][i]['start']).replace(tzinfo=timezone.utc).astimezone(tz=None)
		showEnd = parser.parse(stationData['items'][i]['end']).replace(tzinfo=timezone.utc).astimezone(tz=None)
		duration = stationData['items'][i]['duration']
		# Only add show if it starts the same day and is not autoplay
		if stationData['items'][i]['category'] != 'Automation' and showStart.date()==date.today():
			todaysRecordingSchedule.append({
					'showName': showName,
					'showStart' : showStart,
					'showEnd' : showEnd,
					'duration' : duration
					# 'email' : get email address
			})
	return todaysRecordingSchedule

def sendToDJ(fileName):
	#https://show-bucket-test.s3.us-west-1.amazonaws.com/2022-10-17_The_Salad_Bowl.mp3
	s = smtplib.SMTP('smtp.gmail.com', 587)
	s.starttls()
	s.login(EMAIL, PASSWORD)
	SUBJECT = 'Recording Link'
	TEXT = 'https://show-bucket-test.s3.us-west-1.amazonaws.com/' + fileName +'.mp3'
	message = 'Subject: {}\n\n{}'.format(SUBJECT, TEXT)
	s.sendmail("automation@kscu.org", "jeffreychen2168@gmail.com", message)
	s.quit()

def sendToS3(todaysRecordingSchedule):
	# Old files can be removed automatically through S3
	# Send files from EC2 to S3 and delete them in EC2
	# show-bucket-test needs to be updated to final account
	for i in range(len(fileName)):
		show = todaysRecordingSchedule[i]
		fileName = str(show['showStart'].date()) + '_' + show['showName']
		sendStr = 'aws s3 cp '
		sendStr = sendStr + fileName + ' s3://show-bucket-test'
		os.system(sendStr)
		os.system('rm ' + fileName)
		# https://show-bucket-test.s3.us-west-1.amazonaws.com/2022-10-17_The_Salad_Bowl.mp3
		downloadStr = 'https://show-bucket-test.s3.us-west-1.amazonaws.com/'
		downloadStr = downloadStr + fileName + '.mp3'
		sendToDJ(fileName)

def record(duration, fileName):
	# Create string in the format below:
	# 'ffmpeg -i http://kscu.streamguys1.com:80/live -t "3600" -y output.mp3'
	commandStr = 'ffmpeg -i http://kscu.streamguys1.com:80/live -t '
	commandStr = commandStr + "'" + duration + "' -y " + fileName + ".mp3"
	os.system(commandStr)

def runSchedule(todaysRecordingSchedule):
	recorderSchedule = sched.scheduler(time.time, time.sleep)
	# For each of the items in today's schedule
	# Add to recording schedule
	# Convert to epoch time for the enterabs function
	for i in range(len(todaysRecordingSchedule)):
		show = todaysRecordingSchedule[i]
		fileName = str(show['showStart'].date()) + '_' + show['showName']
		duration = str(show['duration'])
		epochStart = show['showStart'].strftime('%s')
		recorderSchedule.enterabs(int(epochStart), 0, record, argument=(duration, fileName))
	recorderSchedule.run()
	# At the end of the day, files will be sent out
	# Avoid recording delay from uploading files between shows
	if recorderSchedule.empty():
		sendToS3(todaysRecordingSchedule)

while True:
	currentTime = datetime.now().strftime("%H:%M")
	print(currentTime)
	if currentTime == "06:55":
		runSchedule(getTodaysShows())
	time.sleep(60)

