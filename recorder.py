from datetime import date, datetime, timezone # https://docs.python.org/3/library/datetime.html
import ffmpeg # https://kkroening.github.io/ffmpeg-python/
import sched, time # https://pythontic.com/concurrency/scheduler/introduction
import os
from dateutil import parser
import requests

def getTodaysShows():
	stationData = requests.get(f"https://spinitron.com/api/shows?access-token=fsr9w2R8irUUqUkze_QUcyB3&count=15")

	# Check for a successful request
	if stationData.status_code != 200:
		print(stationData.status_code)
	stationData = stationData.json()

	# Structure of dailyRecordingSchedule = [
	# 	{
	# 		'showName': 'Name of Show 1'
	# 		'showStart' : datetime,
	# 		'showEnd': datetime,
	# 		'duration': int
	# 	},
	# 	{
	# 		'showName': 'Name of Show 2'
	# 		'showStart' : datetime,
	# 		'showEnd': datetime,
	# 		'duration': int
	# 	},
	# ]
	# 
	# Time will take into consideration Daylight Savings

	todaysRecordingSchedule = []

	for i in range(len(stationData['items'])):
		showName = stationData['items'][i]['title']
		showStart = parser.parse(stationData['items'][i]['start']).replace(tzinfo=timezone.utc).astimezone(tz=None)
		showEnd = parser.parse(stationData['items'][i]['end']).replace(tzinfo=timezone.utc).astimezone(tz=None)
		duration = stationData['items'][i]['duration']	
		if stationData['items'][i]['category'] != 'Automation' and showStart.date()==date.today():
			todaysRecordingSchedule.append({
					'showName': showName,
					'showStart' : showStart,
					'showEnd' : showEnd,
					'duration' : duration
			})

	return todaysRecordingSchedule

todaysRecordingSchedule = getTodaysShows()
print(todaysRecordingSchedule)
recorderSchedule = sched.scheduler(time.time, time.sleep)
# ffmpeg location needs to be updated depending on system
ffmpeg = '/opt/homebrew/bin/ffmpeg'

# Create string in the format below:
# 'ffmpeg -i http://kscu.streamguys1.com:80/live -t "3600" -y output.mp3'
def record(duration, showName, date):
	showName = "_".join(showName.split())
	commandStr = 'ffmpeg -i http://kscu.streamguys1.com:80/live -t '
	commandStr = commandStr + "'" + str(duration) + "' -y " + str(date) + "_" + showName + ".mp3"
	os.system(commandStr)

def runSchedule():
	# For each of the items in today's schedule
	# Add to recording schedule
	# Convert to epoch time for the enterabs function
	for i in range(len(todaysRecordingSchedule)):
			show = todaysRecordingSchedule[i]
			epochStart = show['showStart'].strftime('%s')
			recorderSchedule.enterabs(int(epochStart), 0, record, argument=(show['duration'], show['showName'], show['showStart'].date()))
	print(recorderSchedule.queue)
	recorderSchedule.run()

while True:
	currentTime = datetime.now().strftime("%H:%M")
	if currentTime == "12:05":
		runSchedule()
	time.sleep(60)

