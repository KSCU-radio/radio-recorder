from getTodaysShows import *
import datetime # https://docs.python.org/3/library/datetime.html
import ffmpeg # https://kkroening.github.io/ffmpeg-python/
import sched, time # https://pythontic.com/concurrency/scheduler/introduction
import os

todaysRecordingSchedule = getTodaysShows()
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

# For each of the items in today's schedule
# Add to recording schedule
# Convert to epoch time for the enterabs function
for i in range(len(todaysRecordingSchedule)):
		show = todaysRecordingSchedule[i]
		epochStart = show['showStart'].strftime('%s')
		recorderSchedule.enterabs(epochStart, 0, record, argument=(show['duration'], show['showName'], show['showStart'].date()))
#print(recorderSchedule.queue)
recorderSchedule.run()

