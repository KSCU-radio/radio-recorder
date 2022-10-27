from datetime import date, datetime, timezone # https://docs.python.org/3/library/datetime.html
import ffmpeg # https://kkroening.github.io/ffmpeg-python/
import sched, time # https://pythontic.com/concurrency/scheduler/introduction
import os
from dateutil import parser
import requests
from dotenv import load_dotenv
import smtplib
import re

load_dotenv()

API_KEY = os.getenv('API_KEY')
EMAIL = os.getenv('EMAIL')
PASSWORD = os.getenv('PASSWORD')

ffmpeg = '/usr/bin/ffmpeg'

def getEmail(link):
	persona = requests.get(link).json()
	return persona["email"]

def getTodaysShows():
	stationData = requests.get(f"https://spinitron.com/api/shows?access-token={API_KEY}&count=24")

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

	for showInfo in stationData['items']:
		showName = showInfo['title']
		showFileName = ''.join(c for c in showName if c.isalnum())
		showStart = parser.parse(showInfo['start']).replace(tzinfo=timezone.utc).astimezone(tz=None)
		showEnd = parser.parse(showInfo['end']).replace(tzinfo=timezone.utc).astimezone(tz=None)
		duration = showInfo['duration']
		# Only add show if it starts the same day and is not autoplay
		if showInfo['category'] != 'Automation':
			hrefLink = showInfo["_links"]["personas"][0]["href"]
			email = getEmail(hrefLink)
			# Need to add API hit to get email address
			todaysRecordingSchedule.append({
					'showName' : showName,
					'showFileName': str(showStart.date()) + '_' + showFileName + '.mp3',
					'showStart' : showStart,
					'showEnd' : showEnd,
					'duration' : duration,
					'email' : email
			})
	return todaysRecordingSchedule

def sendToDJ(fileName, email, showName):
	print('sending to DJ')
	# check for valid email
	regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
	if(re.fullmatch(regex, email)) is None:
		email = "gm@kscu.org"

	# https://kscu.s3.us-west-1.amazonaws.com/2022-10-17_TheSaladBowl.mp3
	downloadStr = 'https://kscu.s3.us-west-1.amazonaws.com/' + fileName

	s = smtplib.SMTP('smtp.gmail.com', 587)
	s.starttls()
	s.login(EMAIL, PASSWORD)
	SUBJECT = f"Recording Link - {showName}"
	text = """
	Hey!
	
	We're testing a new system to automatically record and send you your shows.
	This link is valid for 5 days so please save this file to your local machine.

	If there's any issues with this system, please let us know by emailing gm@kscu.org.
	
	Peace to every crease on your brain,
	KSCU <3
	"""
	text += downloadStr
	message = 'Subject: {}\n\n{}'.format(SUBJECT, text)
	s.sendmail(EMAIL, email, message)
	s.quit()

def sendToS3(fileName):
	# Old files can be removed automatically through S3
	# Send files from EC2 to S3 and delete them in EC2
	sendStr = 'aws s3 cp ' + fileName + ' s3://kscu'
	os.system(sendStr)
	os.system('rm ' + fileName)

def record(duration, showInfo):
	# Create string in the format below:
	# 'ffmpeg -i http://kscu.streamguys1.com:80/live -t "3600" -y output.mp3'
	commandStr = "ffmpeg -i http://kscu.streamguys1.com:80/live -t '" + duration + "' -y " + showInfo["showFileName"]
	os.system(commandStr)
	sendToS3(showInfo["showFileName"])
	sendToDJ(showInfo["showFileName"], showInfo["email"], showInfo["showName"])

def runSchedule(todaysRecordingSchedule):

	# For each of the items in today's schedule
	# Add to recording schedule
	# Convert to epoch time for the enterabs function
	for showInfo in todaysRecordingSchedule:
		duration = str(showInfo['duration'])
		epochStart = int(showInfo['showStart'].strftime('%s'))
		recorderSchedule.enterabs(epochStart, 0, record, argument=(duration, showInfo))
	recorderSchedule.run()
	# At the end of the day, files will be sent out
	# Avoid recording delay from uploading files between shows

recorderSchedule = sched.scheduler(time.time, time.sleep)
while True:
	if recorderSchedule.empty() and datetime.now().strftime("%H:%M")[-2:] == '00':
		runSchedule(getTodaysShows())
