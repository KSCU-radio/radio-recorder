from datetime import date, datetime, timezone # https://docs.python.org/3/library/datetime.html
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

def getDJInfo(link):
	persona = requests.get(link).json()
	djInfo = {}
	djInfo['email'] = persona['email']
	djInfo['id'] = persona['id']
	djInfo['dj'] = persona['name']
	return djInfo

def getTodaysShows():
	print('Grabbing next 24 shows')
	stationData = requests.get(f"https://spinitron.com/api/shows?access-token={API_KEY}&count=24")

	# Check for a successful request
	if stationData.status_code != 200:
		print(stationData.status_code)
	stationData = stationData.json()

	todaysRecordingSchedule = []
	illegalChar = {'#', '%', '&', '{', '}', '\\', '$', '!', "'", '"', ':', '@', '<', '>', '*', '?', '/', '+', '`', '|', '=', ' ', '.', '_', '-', '.', ','}

	for showInfo in stationData['items']:
		djInfo = getDJInfo(showInfo["_links"]["personas"][0]["href"])
		email = djInfo['email']
		dj = djInfo['dj']
		id = djInfo['id']
		showStart = parser.parse(showInfo['start']).replace(tzinfo=timezone.utc).astimezone(tz=None)
		showEnd = parser.parse(showInfo['end']).replace(tzinfo=timezone.utc).astimezone(tz=None)
		duration = showInfo['duration']
		showName = showInfo['title']
		showFileName = ''.join(c for c in showName if c not in illegalChar)
		if showFileName == '':
			showFileName = id
		# Only add show if it starts the same day and is not autoplay
		if showInfo['category'] != 'Automation' and int(showEnd.strftime('%s'))>int(time.time()):
			# Need to add API hit to get email address
			todaysRecordingSchedule.append({
					'showName' : showName,
					'showFileName': str(showStart.date()) + '_' + showFileName + '.mp3',
					'showStart' : showStart,
					'showEnd' : showEnd,
					'duration' : duration,
					'email' : email,
					'dj' : dj
			})
	print('Grabbing next 24 shows complete')
	return todaysRecordingSchedule

def sendToDJ(fileName, email, showName, dj):
	print('Sending email to DJ')
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
	text = f"""
	Hey {dj}! 
	
	This is an automated email from KSCU. 

	You can use the link below to download your show and save it to your computer.
	We only keep your recording for 90 days so you will need to download it to your computer to keep it permanently.
	"""

	text += downloadStr + '\n\n'

	text += """If there's any issues with this system, please let us know by emailing gm@kscu.org.
	
	Much love and respect,
	KSCU 103.3 FM
	The Underground Sound
	"""
	
	message = 'Subject: {}\n\n{}'.format(SUBJECT, text).encode()
	s.sendmail(EMAIL, email, message)
	s.quit()
	print('Email sent to DJ')

def sendToS3(fileName):
	print('Sending file to S3')
	# Old files can be removed automatically through S3
	# Send files from EC2 to S3 and delete them in EC2
	sendStr = 'aws s3 cp ' + fileName + ' s3://kscu'
	os.system(sendStr)
	os.system('rm ' + fileName)
	print('File sent to S3')

def record(duration, showInfo):
	print('Recording ' + datetime.now().strftime("%H:%M:%S"))
	# Create string in the format below:
	# 'ffmpeg -i http://kscu.streamguys1.com:80/live -t "3600" -y output.mp3'
	commandStr = "ffmpeg -i http://kscu.streamguys1.com:80/live -t '" + duration + "' -y " + showInfo["showFileName"]
	os.system(commandStr)
	print('Recording Complete')
	sendToS3(showInfo["showFileName"])
	sendToDJ(showInfo["showFileName"], showInfo["email"], showInfo["showName"], showInfo["dj"])

def runSchedule(todaysRecordingSchedule):
	print('Running Schedule')
	# For each of the items in today's schedule
	# Add to recording schedule
	# Convert to epoch time for the enterabs function
	for showInfo in todaysRecordingSchedule:
		duration = str(showInfo['duration'])
		epochStart = int(showInfo['showStart'].strftime('%s'))
		recorderSchedule.enterabs(epochStart, 0, record, argument=(duration, showInfo))
	recorderSchedule.run()
	print('Schedule Complete')
	# At the end of the day, files will be sent out
	# Avoid recording delay from uploading files between shows

recorderSchedule = sched.scheduler(time.time, time.sleep)

while True:
	if recorderSchedule.empty() and datetime.now().strftime("%H:%M")[-2:] == '00':
		print('Grabbing next 24 Shows')
		runSchedule(getTodaysShows())
	time.sleep(1) # If there is not sleep, the CPU usage goes crazy while waiting
