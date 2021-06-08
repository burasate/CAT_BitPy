import pandas as pd
import numpy as np
import json,os,time
import datetime as dt
import gSheet
import kbApi
import lineNotify
from bitkub import Bitkub

rootPath = os.path.dirname(os.path.abspath(__file__))
dataPath = rootPath+'/data'
histPath = dataPath + '/hist'
imgPath = dataPath + '/analysis_img'
configPath = dataPath + '/config.json'
presetPath = dataPath + '/preset.json'
systemPath = dataPath + '/system.json'
configJson = json.load(open(configPath))
presetJson = json.load(open(presetPath))
systemJson = json.load(open(systemPath))

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
mornitorFilePath = dataPath + '/mornitor.csv'
transacFilePath = dataPath + '/transaction.csv'

def isInternetConnect(*_):
    url = 'http://google.com'
    connectStatus = requests.get(url).status_code
    if connectStatus == 200:
        return True
    else:
        return False

def getBalance(idName):
    API_KEY = configJson[idName]['bk_apiKey']
    API_SECRET = configJson[idName]['bk_apiSecret']
    if API_KEY == '' or API_SECRET == '' :
        print('this user have no API KEY or API SECRET to send order')
        return None
    bitkub = Bitkub()
    bitkub.set_api_key(API_KEY)
    bitkub.set_api_secret(API_SECRET)
    balance = bitkub.balances()
    data = {}
    if balance['error'] == 0 :
        for sym in balance['result']:
            if balance['result'][sym]['available'] > 0 :
                data[sym] = {
                    'available' : balance['result'][sym]['available'],
                    'reserved' : balance['result'][sym]['reserved']
                }
    return data

def CreateBuyOrder(idName,symbol):
    if not symbol.__contains__('THB_'):
        print('symbol name need contains THB_')
        return None
    API_KEY = configJson[idName]['bk_apiKey']
    API_SECRET = configJson[idName]['bk_apiSecret']
    if API_KEY == '' or API_SECRET == '' :
        print('this user have no API KEY or API SECRET to send order')
        return None
    bitkub = Bitkub()
    bitkub.set_api_key(API_KEY)
    bitkub.set_api_secret(API_SECRET)
    balance = getBalance(idName)
    percentageBalanceUsing = configJson[idName]['percentageBalanceUsing']
    system = configJson[idName]['system']
    size = int(systemJson[system]['size'])
    portSize = len(list(balance))-1
    budget = balance['THB']['available']
    sizedBudget = (budget / (size-portSize)) * (percentageBalanceUsing/100)
    #print(sizedBudget)
    result = bitkub.place_bid(sym=symbol, amt=sizedBudget, typ='market')
    print(result)

def CreateSellOrder(idName,symbol):
    if not symbol.__contains__('THB_'):
        print('symbol name need contains THB_')
        return None
    API_KEY = configJson[idName]['bk_apiKey']
    API_SECRET = configJson[idName]['bk_apiSecret']
    if API_KEY == '' or API_SECRET == '' :
        print('this user have no API KEY or API SECRET to send order')
        return None
    bitkub = Bitkub()
    bitkub.set_api_key(API_KEY)
    bitkub.set_api_secret(API_SECRET)
    balance = getBalance(idName)
    sym = symbol.replace('THB_','')
    if not sym in list(balance):
        print('not found [{}] in balance'.format(sym))
        return None
    amount = balance[sym]['available']
    result = bitkub.place_ask(sym=symbol, amt=amount, typ='market')
    print(result)

def Reset(*_):
    print('---------------------\nReset\n---------------------')
    global mornitorFilePath
    global transacFilePath
    if not os.path.exists(mornitorFilePath):
        return None
    m_df = pd.read_csv(mornitorFilePath)
    t_df = pd.read_csv(transacFilePath)
    deleteList = []

    m_user_list = m_df['User'].unique().tolist()
    t_user_list = t_df['User'].unique().tolist()
    for user in m_user_list:
        print('Checking User {} in Mornitor {}'.format(user,m_user_list))
        if not user in list(configJson):
            deleteList.append(user)
    for user in t_user_list:
        print('Checking User {} in Transaction {}'.format(user, t_user_list))
        if not user in list(configJson):
            deleteList.append(user)

    #Sending Restart
    for user in list(configJson):
        systemName = configJson[user]['system']
        if bool(configJson[user]['reset']):
            gSheet.setValue('Config',findKey='idName',findValue=user,key='reset',value=0)
            gSheet.setValue('Config', findKey='idName', findValue=user, key='lastReport', value=time.time())
            text = '[ Reset Portfoilo ]\n' +\
                   'User ID : {} \n'.format(user) +\
                   'Preset ID : {} \n'.format(configJson[user]['preset']) +\
                   'System ID : {} \n'.format(systemName) +\
                   'Size : {} \n'.format(systemJson[systemName]['size']) +\
                   'Take Profit By : {} \n'.format(systemJson[systemName]['takeProfitBy']) +\
                   'Target Profit : {}%'.format(systemJson[systemName]['percentageProfitTarget'])
            lineNotify.sendNotifyMassage(configJson[user]['lineToken'],text)
            print(text)

    for user in deleteList:
        print('delete [ {} ]'.format(user))
        m_df = m_df[m_df['User'] != user]
        t_df = t_df[t_df['User'] != user]

    m_df.to_csv(mornitorFilePath,index=False)
    t_df.to_csv(transacFilePath, index=False)
    print('User Reset')

def Transaction(idName,code,symbol,change):
    global transacFilePath
    date_time = str(dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    data = {
        'dateTime' : [date_time],
        'User' : [idName],
        'Code' : [code],
        'Symbol' : [symbol],
        'Change%' : [change]
    }
    col = ['dateTime']
    if not os.path.exists(transacFilePath):
        entry_df = pd.DataFrame(columns=list(data))
        entry_df.to_csv(transacFilePath, index=False)
    entry_df = pd.read_csv(transacFilePath)

    # Checking Column
    for c in list(data):
        if not c in entry_df.columns.tolist():
            entry_df[c] = None
    rec = pd.DataFrame(data)
    entry_df = entry_df.append(rec,ignore_index=True)
    entry_df.to_csv(transacFilePath,index=False)

def MornitoringUser(idName,sendNotify=True):
    isActive = bool(configJson[idName]['active'])
    isReset = bool(configJson[idName]['reset'])
    if isActive == False:
        return None
    print('---------------------\n[ {} ]  Monitoring\n---------------------'.format(idName))
    now = round(time.time())
    reportHourDuration = round( float(((now - configJson[idName]['lastReport'])/60)/60),2 )
    preset = configJson[idName]['preset']
    system = configJson[idName]['system']
    token = configJson[idName]['lineToken']
    size = int(systemJson[system]['size'])
    profitTarget = float(systemJson[system]['percentageProfitTarget'])
    print('Last Report  {} Hour Ago / Report Every {} H'.format(reportHourDuration, configJson[idName]['reportEveryHour']))

    signal_df = pd.read_csv(dataPath+'/signal.csv')
    #signal_df = signal_df[signal_df['Rec_Date'] == signal_df['Rec_Date'].max()]
    signal_df = signal_df[
        (signal_df['Rec_Date'] == signal_df['Rec_Date'].max()) &
        (signal_df['Preset'] == preset)
    ]
    signal_df.reset_index(inplace=True)

    # Select Entry
    entry_df = signal_df
    #entry_df['Change4HR%_Abs'] = entry_df['Change4HR%'].abs()
    entry_df = entry_df[
        ( entry_df['Rec_Date'] == entry_df['Rec_Date'].max() ) &
        ( entry_df['Signal'] == 'Entry' ) &
        ( entry_df['Preset'] == preset )
        #( entry_df['Change4HR%'] >= 0 ) &
        #( entry_df['Close'] <= entry_df['BreakOut_M'] )
    ]
    #entry_df = entry_df.sort_values(['Change4HR%_Abs','Value_M'], ascending=[True,False])
    entry_df = entry_df.sort_values(['Change4HR%','Value_M'], ascending=[False,False])
    #entry_df = entry_df.head(size) # Select Count
    entry_df.reset_index(inplace=True)
    #print(entry_df) # Signal Checking

    # New Column For Signal DF
    signal_df['User'] = idName
    signal_df['Buy'] = signal_df['Close']
    signal_df['Market'] = signal_df['Close']
    signal_df['Profit%'] = ((signal_df['Market'] - signal_df['Buy']) / signal_df['Buy']) * 100
    signal_df['Max_Drawdown%'] = 0.0

    # New Column For Entry DF
    entry_df['User'] = idName
    entry_df['Buy'] = entry_df['Close']
    entry_df['Market'] = entry_df['Close']
    entry_df['Profit%'] = ( ( entry_df['Market'] - entry_df['Buy'] ) / entry_df['Buy'] ) * 100
    entry_df['Max_Drawdown%'] =  0.0

    colSelect = ['User','Symbol','Signal','Buy','Market',
                 'Profit%','Max_Drawdown%','Change4HR%',
                 'Value_M','BreakOut_H','BreakOut_M',
                 'BreakOut_L','Rec_Date']
    entry_df = entry_df[colSelect]
    #print(entry_df[['Symbol','Signal','Change4HR%']])
    print('Select Entry {}'.format(entry_df['Symbol'].to_list()))

    # Mornitor data frame
    global mornitorFilePath
    if not os.path.exists(mornitorFilePath):
        morn_df = pd.DataFrame(columns=colSelect)
        morn_df.to_csv(mornitorFilePath,index=False)
    morn_df = pd.read_csv(mornitorFilePath)

    # Checking Column
    for c in colSelect:
        if not c in morn_df.columns.tolist():
            morn_df[c] = None

    #Portfolio
    portfolioList = morn_df[morn_df['User'] == idName]['Symbol'].tolist()
    print('{} Portfolio have {}'.format(idName, portfolioList))

    # Buy Notify
    # ==============================
    for i in range(entry_df['Symbol'].count()):
        row = entry_df.iloc[i]
        buy_condition =  (
            (len(portfolioList) < size) and  #Port is not full
            (not row['Symbol'] in portfolioList) and # Not Symbol in Port
            (row['Buy'] > row['BreakOut_L']) and # Price Not Equal Break Low
            (row['Buy'] < row['BreakOut_M']) # Price Not Equal Break Low
        )
        if buy_condition: # Buy Condition
            text = '[ Buy ] {}\n{} Bath'.format(row['Symbol'],row['Buy'])
            quote = row['Symbol'].split('_')[-1]
            imgFilePath = imgPath + os.sep + '{}_{}.png'.format(preset,quote)
            print(text)
            print(imgFilePath)
            if sendNotify:
                lineNotify.sendNotifyImageMsg(token, imgFilePath, text)
            morn_df = morn_df.append(row,ignore_index=True)
            portfolioList.append(row['Symbol'])
            Transaction(idName, 'Buy', row['Symbol'], (systemJson[system]['percentageComission']/100) * -1)
            CreateBuyOrder(idName,row['Symbol'])
        elif len(portfolioList) >= size: # Port is Full
            print('Can\'t Buy More\nportfolio is full')
            break
    # ==============================

    # Update Trailing (If Close > Mid)
    for i in range(signal_df['Symbol'].count()):
        row = signal_df.iloc[i]
        trailing_condition = (
                (row['Symbol'] in portfolioList) and
                (row['Close'] > row['BreakOut_M'])
        )
        if trailing_condition:
            morn_df = morn_df.append(row, ignore_index=True)
            print('Updated Trailing ( {} )'.format(row['Symbol']))

    morn_df = morn_df[colSelect]

    # Ticker ( Update Last Price as 'Market' )
    ticker = kbApi.getTicker()
    for sym in ticker:
        if not sym in morn_df['Symbol'].unique().tolist():
            continue
        morn_df.loc[morn_df['Symbol'] == sym, 'Market'] = ticker[sym]['last']
    print('Update Market Price')

    # Calculate in Column
    print('Profit Calculating...')
    morn_df['Buy'] = morn_df.groupby(['User','Symbol']).transform('first')['Buy']
    morn_df['Profit%'] = ((morn_df['Market'] - morn_df['Buy']) / morn_df['Buy']) * 100
    morn_df['Profit%'] = morn_df['Profit%'].round(2)
    morn_df.loc[(morn_df['Profit%'] < 0.0) & (morn_df['Max_Drawdown%'] == 0.0), 'Max_Drawdown%'] = morn_df['Profit%'].abs()
    morn_df.loc[(morn_df['Profit%'] > 0.0) & (morn_df['Max_Drawdown%'] == 0.0), 'Max_Drawdown%'] = 0.0
    morn_df.loc[(morn_df['Profit%'] < 0.0) & (morn_df['Profit%'] < morn_df['Max_Drawdown%'].abs()*-1),
                'Max_Drawdown%'] = morn_df['Profit%'].abs()
    morn_df['Max_Drawdown%'] = morn_df.groupby(['User', 'Symbol'])['Max_Drawdown%'].transform('max')
    morn_df.drop_duplicates(['User','Symbol'],keep='last',inplace=True)
    morn_df.to_csv(mornitorFilePath, index=False)

    # Reload mornitor again
    morn_df = pd.read_csv(mornitorFilePath)
    morn_df = morn_df.sort_values(['User','Profit%'], ascending=[True,False])
    holdList = morn_df[
        (morn_df['User'] == idName) &
        (morn_df['Profit%'] > 0.0)
    ].head(size)['Symbol'].tolist()

    # Sell Notify
    # ==============================
    sell_df = signal_df[
        (signal_df['Signal'] == 'Exit') &
        (signal_df['Preset'] == preset)
        ]
    sellList = []
    for i in range(morn_df['Symbol'].count()):
        row = morn_df.iloc[i]
        text = '[ Sell ] {}\n{} Bath ({}%)'.format(row['Symbol'], row['Market'],row['Profit%'])
        sell_condition = (
                ( row['Market'] < row['BreakOut_L'] ) &
                ( row['User'] == idName )
                )
        if row['BreakOut_L'] < row['Buy'] :  # Edit Sell Condition When Triling < Buy
            sell_condition = (
                    (row['Market'] < row['BreakOut_M']) &
                    (row['User'] == idName)
            )
        if sell_condition:
            print(text)
            if sendNotify:
                lineNotify.sendNotifyMassage(token, text)
            sellList.append(
                {
                    'User': row['User'],
                    'Symbol' : row['Symbol']
                 }
            )
    # ==============================

    #Report
    report_df = morn_df[morn_df['User'] == idName]
    report_df = report_df.sort_values(['Profit%'], ascending=[False])

    #Portfolio report
    if report_df['Symbol'].count() != 0 and reportHourDuration >= configJson[idName]['reportEveryHour']:
        gSheet.setValue('Config', findKey='idName', findValue=idName, key='lastReport', value=time.time())
        text = '[ Report ]\n' +\
                '{}\n'.format( ' , '.join(report_df['Symbol'].tolist()) ) +\
                'Profit Sum {}%\n'.format(report_df['Profit%'].sum().round(2)) + \
               'Profit Average {}%'.format(report_df['Profit%'].mean().round(2))
        print(text)
        if sendNotify:
            lineNotify.sendNotifyMassage(token, text)

    #Take profit all
    profit_condition = report_df['Profit%'].mean() >= profitTarget
    if systemJson[system]['takeProfitBy'] == 'Sum':
        profit_condition = report_df['Profit%'].sum() >= profitTarget
    if profit_condition or isReset:
        gSheet.setValue('Config', findKey='idName', findValue=idName, key='reset', value=1)
        text = '[ Take Profit ]\n' + \
               'Target Profit {}%\n'.format(profitTarget) + \
               'Profit Sum {}%\n'.format(report_df['Profit%'].sum().round(2)) + \
               'Profit Average {}%'.format(report_df['Profit%'].mean().round(2))
        print(text)
        if sendNotify:
            lineNotify.sendNotifyMassage(token, text)

        # Prepare Sell When Take Profit or Reset
        for sym in report_df['Symbol'].tolist():
            if sym in sellList:
                continue
            sellList.append(
                {
                    'User': idName,
                    'Symbol': sym
                }
            )

    # Sell And Delete Symbol
    for i in sellList:
        profit = morn_df[(morn_df['User'] == i['User']) & (morn_df['Symbol'] == i['Symbol'])]['Profit%'].tolist()[0]
        morn_df = morn_df.drop(
            morn_df[(morn_df['User'] == i['User']) & (morn_df['Symbol'] == i['Symbol'])].index
        )
        if systemJson[system]['takeProfitBy'] == 'Average':
            profit = profit/size
        Transaction( i['User'], 'Sell', i['Symbol'], ((systemJson[system]['percentageComission'] / 100) * -1) + profit )
        CreateSellOrder(i['User'],i['Symbol'])

    #Finish
    morn_df.to_csv(mornitorFilePath, index=False)
    print('{} Update Finished'.format(idName))

def AllUser(*_):
    os.system('cls||clear')
    global mornitorFilePath
    global transacFilePath
    for user in configJson:
        if os.name == 'nt':
            print('[For Dev Testing...]')
            MornitoringUser(user,sendNotify=False)
        else:
            try:
                MornitoringUser(user)
            except Exception as e:
                print('\nError To Record ! : {}  then skip\n'.format(e))
                continue
    while isInternetConnect and not os.name == 'nt':
        try:
            #print('Uploading mornitoring data...')
            if os.path.exists(mornitorFilePath):
                gSheet.updateFromCSV(mornitorFilePath, 'Mornitor')
            #print('Upload mornitoring data finish')
            #print('Uploading Transaction data...')
            if os.path.exists(transacFilePath):
                gSheet.updateFromCSV(transacFilePath, 'Transaction')
            #print('Upload Transaction data finish')
        except:
            pass
        else:
            break
        time.sleep(10)
        #if gSheet.getAllDataS('Mornitor') != []:
            #break



if __name__ == '__main__' :
    #import update
    #update.updateConfig()
    #configJson = json.load(open(configPath))
    #update.updateSystem()
    #systemJson = json.load(open(systemPath))

    #Reset()
    #MornitoringUser('CryptoBot')
    #MornitoringUser('user1')
    #CreateBuyOrder('user1','THB_USDC')
    #CreateSellOrder('user1','THB_USDC')
    #AllUser()
    #Transaction('idName', 'code', 'symbol', 'change')
    """
    morn_df = pd.read_csv(dataPath + '/mornitor.csv')
    morn_df = morn_df.sort_values(['User', 'Profit%'], ascending=[True, False])
    holdList = morn_df[
        (morn_df['User'] == 'CryptoBot') &
        (morn_df['Profit%'] >= 0.0)
        ].head(5)['Symbol'].tolist()
    print(holdList)
    """
    pass
