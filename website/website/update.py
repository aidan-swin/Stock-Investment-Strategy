import yfinance as yf
import pandas as pd
from datetime import datetime
from selenium import webdriver
from bs4 import BeautifulSoup as bs
import time
import random
import warnings

# Define a function to scrape dividend information for a given stock code
def scrape_dividend_info(stock_code, start_date, end_date):
    status = ""
    try:
        # Create an empty dataframe to store dividend information
        div_info_final = pd.DataFrame()
        
        url = 'https://www.klsescreener.com/v2/stocks/view/' + stock_code
        driver.get(url) 
        content = driver.page_source
        soup = bs(content, 'html.parser')

        # Scrape table
        tables = soup.find_all('table')
        # Read tables with Pandas read_html()
        dfs = pd.read_html(str(tables))
        
        # Find the table that contains column 'Payment Date'
        i = 0
        has_div = False
        while i < len(dfs) and not has_div:
            n = 0
            while n < len(dfs[i].columns):
                if dfs[i].columns[n] == 'Payment Date':
                    has_div = True
                n += 1
            i += 1

        if has_div:
            div_info2 = dfs[i - 1]

            # Change data types    
            div_info2['Financial Year'] = pd.to_datetime(div_info2['Financial Year'])
            div_info2['Financial Year'] = pd.to_datetime(div_info2['Financial Year'].dt.strftime('%Y-%m-%d'))

            # Filter data between two dates    
            filtered_df = div_info2.loc[(div_info2['Financial Year'] >= pd.to_datetime(start_date))
                                        & (div_info2['Financial Year'] < pd.to_datetime(end_date))]
            filtered_df.reset_index(drop=True, inplace=True)

            # Check whether the filtered_df is empty
            if filtered_df.empty:
                status = 'N'
                print(f'Stock code: {stock_code} - no dividend info between {start_date} to {end_date}')
            else:
                status = 'Y'
                filtered_df['Stock Code'] = stock_code
                filtered_df['Year'] = filtered_df['Financial Year'].dt.strftime('%Y')
                filtered_df['Status'] = status
                div_info_final = div_info_final.append(filtered_df, ignore_index=True)
                print(f'Stock code: {stock_code} - yes')
        else:
            status = 'N'
            print(f'Stock code: {stock_code} - no dividend info')

    except Exception as e:
        print(f'Stock code: {stock_code} - Loading failed due to Timeout')
        print(e)

    return div_info_final


# update.py
def get_data(latest_dates):
    

    # Define the end date (current day)
    end_date = datetime.today().strftime('%Y-%m-%d')   # Replace with the current date in 'YYYY-MM-DD' format

    combined_data = []  # To store successful data
    dividend_info_list = []
    error_symbols = []  # To store symbols with errors

    global driver
    # Connect/open the Chrome webdriver
    driver = webdriver.Chrome()
    driver.implicitly_wait(60)

# Loop through each stock symbol and retrieve its historical data
    for row in latest_dates:
        symbol = row.stock_code
        latest_price_date = row.latest_price_date
        latest_dividend_date = row.latest_dividend_date
        
        try:
            # Use yfinance to retrieve historical data for the symbol
            stock_data = yf.download(symbol + ".KL", start=latest_price_date, end=end_date)
            
            # Create a new DataFrame with 'stock_data' and a 'stock_code' column
            stock_data['stock_code'] = symbol
            
            # Append the DataFrame to the list of successful symbols
            combined_data.append(stock_data)
            # Convert start_date and end_date to datetime objects
            # Print the first few rows of the historical data for demonstration
            # print(f"Stock Symbol: {symbol}")
            # print(stock_data.head())
            dividend_info_list.append(scrape_dividend_info(symbol, latest_dividend_date, end_date))
            
        except Exception as e:
            print(f"Error retrieving data for {symbol}: {e}")
            # Append the unsuccessful symbol to the list
            error_symbols.append(symbol)
        time.sleep(3)

    # After the loop, concatenate all DataFrames into a single DataFrame
    price_df = pd.concat(combined_data)
    dividend_df = pd.concat(dividend_info_list)
    print(dividend_df.head())
    # print(price_df.head())

    # The 'final_df' DataFrame contains the combined historical data for all successful stock symbols
