import requests

stationData = requests.get(f"https://spinitron.com/api/shows?access-token=fsr9w2R8irUUqUkze_QUcyB3&count=10")

# Chceck for a successful request
if stationData.status_code != 200:
	print(stationData.status_code)

stationData = stationData.json()

dailyRecordingSchedule = {}

for i in range(len(stationData['items'])):
	showName = stationData['items'][i]['title']
	showStart = stationData['items'][i]['start']
	showEnd = stationData['items'][i]['end']
	#Timezone -7hrs from the API
	#Do we have to do -8 for DLS
	print(showStart)
	#if showName != 'KSCU Autoplay' and showStart
