import os,json,requests,time
from datetime import datetime as dt
import pandas as pd
import kbApi
import gSheet

rootPath = os.path.dirname(os.path.abspath(__file__))
dataPath = rootPath+'/data'
histPath = dataPath + '/hist'
configPath = dataPath + '/config.json'
configJson = json.load(open(configPath))
presetPath = dataPath + '/preset.json'
presetJson = json.load(open(presetPath))

def isInternetConnect(*_):
    url = 'http://google.com'
    connectStatus = requests.get(url).status_code
    if connectStatus == 200:
        return True
    else:
        return False

def getHistDataframe(*_):
    print('load history data from google sheet...')
    sheetData = gSheet.getAllDataS('History')
    df = pd.DataFrame.from_records(sheetData)
    return df

def updateGSheetHistory(limit = 35000):
    ticker = kbApi.getTicker()
    symbols = kbApi.getSymbol()

    df = pd.DataFrame()
    df = df.append(getHistDataframe())

    date = dt.now().strftime('%Y-%m-%d')
    hour = int(dt.now().strftime('%H'))
    epoch = time.time()
    minute = int(dt.now().strftime('%M'))
    second = int(dt.now().strftime('%S'))
    date_time = str(dt.now().strftime('%Y-%m-%d %H:%M:%S'))


    #backup hist
    backupPath = dataPath + '/hist_backup/cryptoHist_{}_{}.csv'.format(date.replace('-','_'),hour)
    df.to_csv(backupPath, index=False)

    # append backup
    for f in os.listdir(dataPath + '/hist_backup'):
        filePath = dataPath + '/hist_backup/{}'.format(f)
        print(filePath)
        df = df.append(
            pd.read_csv(filePath)
        )

    os.system('cls||clear')
    for data in symbols:
        sym = data['symbol']
        if not sym in ticker:
            continue

        print('{}   {} Baht'.format(sym,ticker[sym]['last']))

        rowData = {
            'epoch': epoch,
            'date': date,
            'hour': hour,
            'minute': minute,
            'second': second,
            'symbol': sym,
            'dateTime': date_time
        }

        for colName in ticker[sym]:
            rowData[colName] = [ticker[sym][colName]]
        df = df.append(
            pd.DataFrame(rowData), ignore_index=True
        )

    # delete duplicate
    df.drop_duplicates(['symbol','date','hour','minute'], keep='last', inplace=True)
    df.sort_index(inplace=True)
    #limit row
    df = df.tail(limit)
    # print(df)

    allHistPath = dataPath + '/cryptoHist.csv'
    df = df[list(rowData)]
    df.to_csv(allHistPath, index=False)

    while isInternetConnect():
        try:
            print('uploading history data...')
            gSheet.updateFromCSV(allHistPath, 'History')
            print('upload history data finish')
        except: pass
        time.sleep(10)
        if gSheet.getAllDataS('History') != []:
            break

def createSymbolHistory(symbol,timeFrame = 'minute'):
    os.system('cls||clear')
    print('create price history ... {}  time frame {}'.format(symbol,timeFrame.upper()))
    df = pd.DataFrame(
        {
            'Day' : [],
            'Date' : [],
            'Open' : [],
            'High' : [],
            'Low' : [],
            'Close' : [],
            'adjClose' : [],
            'Volume' : []
        }
    )

    allHistPath = dataPath + '/cryptoHist.csv'
    histDF = pd.read_csv(allHistPath)
    histDF = histDF[histDF['symbol'] == symbol]

    #set timeframe
    if timeFrame == 'minute':
        group = ['symbol','date','hour','minute']
    elif timeFrame == 'hour':
        group = ['symbol','date','hour']
    elif timeFrame == 'day':
        group = ['symbol','date']

    #transfrom low high by timeframe grp
    histDF['low'] = histDF.groupby(group)['last'].transform('min')
    histDF['high'] = histDF.groupby(group)['last'].transform('max')
    histDF['open'] = histDF.groupby(group)['last'].head(1)
    histDF['open'] = histDF['open'].fillna(method='ffill')
    histDF['close'] = histDF.groupby(group)['last'].tail(1)
    histDF['close'] = histDF['close'].fillna(method='ffill')

    #delete sub timeframe duplicate and clean up
    histDF.drop_duplicates(group, keep='last', inplace=True)
    histDF = histDF.tail(101)
    histDF.reset_index(inplace=True)

    # assign df
    df['Date'] = histDF['dateTime']
    df['Close'] = histDF['close'].round(2)
    df['adjClose'] = histDF['close'].round(2)
    df['Open'] = histDF['open'].round(2)
    df['Low'] = histDF['low'].round(2)
    df['High'] = histDF['high'].round(2)
    df['Volume'] = histDF['baseVolume'].diff(1).abs()
    df['Day'] = histDF.index

    #revese index and save
    df = df.sort_index(ascending=False)
    symbolPath = histPath + os.sep + symbol + '.csv'
    df.to_csv(symbolPath,index=False)

def loadAllHist(timeFrame = 'minute'):
    for f in os.listdir(histPath):
        os.remove(histPath + os.sep + f)

    ticker = kbApi.getTicker()
    symbols = kbApi.getSymbol()
    for data in symbols:
        sym = data['symbol']
        if not sym in ticker:
            continue
        createSymbolHistory(sym,timeFrame)

if __name__ == '__main__':
    #createSymbolHistory('THB_DOGE')
    #updateGSheetHistory()
    #loadAllHist(timeFrame='hour')
    pass
