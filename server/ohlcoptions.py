import requests
import pandas as pd
import datetime
from datetime import timezone
import math
from pymongo import MongoClient
import openpyxl
def get_ohlc_optiondata(optiontype, index, resolution, start_time_date, hours, collection):
    
    def get_historical_atm(unix_start, resolution, index):
        start = unix_start - 3600
        end = unix_start 
        params = {
            'resolution': resolution,
            'symbol': f"{index}USD",
            'start': f"{start}",
            'end': f"{end}"
        }
        response = requests.get("https://cdn.india.deltaex.org/v2/history/candles", params=params)
        data = response.json()['result']
        close = data[1]['close']    
        atm_value = int(math.floor(close / 200.0)) * 200
        return atm_value 
     
    def convert_to_utc_unix(dt):
        """Converts a datetime object to UTC and then to Unix timestamp."""
        utc_dt = dt.astimezone(timezone.utc)
        unix_time = int(utc_dt.timestamp())
        return unix_time

    def dates(start_time_date):
        """Parses the input string into a datetime object."""
        date_obj = datetime.datetime.strptime(start_time_date, "%d-%m-%Y %I:%M %p")
        starttime = datetime.datetime(date_obj.year, date_obj.month, date_obj.day, date_obj.hour, date_obj.minute, date_obj.second)
        return starttime
    
    start_time = dates(start_time_date)
    end_time = start_time + datetime.timedelta(hours=hours)
    # end_time_date = start_time + datetime.timedelta(days=1)
    # Convert to UTC and then to Unix timestamp
    unix_start = convert_to_utc_unix(start_time)
    unix_end = convert_to_utc_unix(end_time)

    # Pass all required arguments to get_historical_atm
    atm_value = get_historical_atm(unix_start, resolution, index)
    symbol = f"{optiontype}-{index}-{atm_value}-{end_time.strftime('%d%m%y')}"
    
    params = {
        'resolution': resolution,
        'symbol': symbol,
        'start': f"{unix_start}",
        'end': f"{unix_end}"
    }
    response = requests.get("https://cdn.india.deltaex.org/v2/history/candles", params=params)

    # Extract the 'result' key which contains the data
    data = response.json()['result']
    close_data = [{'time': entry['time'], 'close': entry['close']} for entry in data]

    # Create a DataFrame
    df = pd.DataFrame(close_data)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df['time'] = df['time'].dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
   
    df['time'] = df['time'].dt.strftime('%H:%M:%S')

    # Prepare the data in the desired format
    date_data = {row['time']: row['close'] for _, row in df.iterrows()}
    document = {
        "expiry": end_time.strftime('%d-%m-%y'),
        "atm_value": atm_value,
        "data": date_data
    }
    collection.insert_one(document)
    
    print(f"Data for {start_time_date} saved to MongoDB.")
    # print(document)

# MongoDB setup
client = MongoClient('mongodb://localhost:27017/')
db = client['ohlc_data']
## be very carefull here 
collection = db['C-ETH-3M-7-PM-1h']

# Looping the function get_ohlc_optiondata for the next 30 days
start_date = '01-07-2024 07:30 PM'
end_date = '31-07-2024 07:30 PM'

current_date = datetime.datetime.strptime(start_date, "%d-%m-%Y %I:%M %p")
end_date = datetime.datetime.strptime(end_date, "%d-%m-%Y %I:%M %p")

while current_date <= end_date:
    start_time_date = current_date.strftime("%d-%m-%Y %I:%M %p")
    get_ohlc_optiondata('C', 'ETH', '1h', start_time_date, 12, collection)
    current_date += datetime.timedelta(days=1)


