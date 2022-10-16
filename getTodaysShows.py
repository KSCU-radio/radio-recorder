from dateutil import parser
from datetime import date, datetime, timezone
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
