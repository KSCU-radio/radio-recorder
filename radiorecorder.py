from dateutil import parser
import datetime
import requests

stationData = requests.get(f"https://spinitron.com/api/shows?access-token=fsr9w2R8irUUqUkze_QUcyB3&count=15")

#Chceck for a successful request
if stationData.status_code != 200:
	print(stationData.status_code)

def isDST(dt):
    if dt.year < 2007:
        raise ValueError()
    dst_start = datetime.datetime(dt.year, 3, 8, 2, 0)
    dst_start += datetime.timedelta(6 - dst_start.weekday())
    dst_end = datetime.datetime(dt.year, 11, 1, 2, 0)
    dst_end += datetime.timedelta(6 - dst_end.weekday())
    return dst_start <= dt < dst_end

stationData = stationData.json()

today = datetime.datetime.today()
isTodayDST = isDST(today)
if isTodayDST:
	n = 7 
else:
	n = 8
today = today.date()
print(today)

dailyRecordingSchedule = []

for i in range(len(stationData['items'])):
	showName = stationData['items'][i]['title']
	showStart = parser.parse(stationData['items'][i]['start']) - datetime.timedelta(hours=n)
	showEnd = parser.parse(stationData['items'][i]['end']) - datetime.timedelta(hours=n)
	duration = stationData['items'][i]['duration']	

	if showName != 'KSCU Autoplay' and showStart.date()==today:
		dailyRecordingSchedule.append({
			showName : {
				'showStart' : showStart,
				'showEnd' : showEnd,
				'duration' : duration
			}
		})

print(dailyRecordingSchedule)

