from crontab import CronTab

def createClock(path, timer):
  cron = CronTab(user=True)
  iter = cron.find_comment('p'+path+'$')
  for i in iter:
    cron.remove(i)
  if timer != "0":
    job = cron.new(command=' ~/.nvm/versions/node/v7.10.1/bin/node ~/dspacenet/api/tickWorker.js ' + path, comment='p'+path+'$')
    job.setall(timer)
  cron.write()


createClock("2",3)