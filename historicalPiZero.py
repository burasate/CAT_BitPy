import os,json,requests,time,random
from datetime import datetime as dt
import kbApi
import gSheet

if not os.name == 'nt':
    time.sleep(60)
    import update
    update.updateConfig()
    update.updatePreset()
    update.updateSystem()
    update.updateAllFile()

rootPath = os.path.dirname(os.path.abspath(__file__))
dataPath = rootPath+'/data'
configPath = dataPath + '/config.json'
configJson = json.load(open(configPath))
presetPath = dataPath + '/preset.json'
presetJson = json.load(open(presetPath))
systemPath = dataPath + '/system.json'
systemJson = json.load(open(systemPath))

def getHistDataframe(*_):
    df = pd.DataFrame()
    sheetData = gSheet.getAllDataS('History')

    for row in sheetData:
        rowData = {}
        for colName in row:
            rowData[colName] = [row[colName]]
        df = df.append(
            pd.DataFrame(rowData),ignore_index=True
        )
    df.sort_index(inplace=True)
    return df

def updateGSheetHistory(*_):
    ticker = kbApi.getTicker()
    symbols = kbApi.getSymbol()
    header = gSheet.getWorksheetColumnName('History')

    isReverse = bool(random.randint(0, 1))
    if isReverse:
        symbols = symbols.reverse()

    os.system('cls||clear')

    for data in symbols:
        sym = data['symbol']
        if not sym in ticker:
            continue

        data = {
            'date': dt.now().strftime('%Y-%m-%d'),
            'hour': int(dt.now().strftime('%H')),
            'epoch': time.time(),
            'minute': int(dt.now().strftime('%M')),
            'second': int(dt.now().strftime('%S')),
            'symbol' : sym,
            'dateTime' : dt.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        for i in ticker[sym]:
            data[i] = ticker[sym][i]
        #print(data)

        row = []
        for col in header:
            row.append(data[col])
        print(row)

        gSheet.addRow('History',row)

if not os.name == 'nt':
    while True:
        try:
            updateGSheetHistory()
        except:
            time.sleep(15)
        else:
            time.sleep(300)


