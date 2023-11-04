import yfinance as yf
import pandas as pd
from datetime import datetime, date
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from bs4 import BeautifulSoup as bs
import time
import random
import warnings

# funtion to get link
def get_link(stock_code):
    
    url='https://www.bursamarketplace.com/index.php'
    driver.get(url)
    
    # Clicking the Search Button
    s= driver.find_element(By.XPATH,'//*[@id="newnav-mobileSearch"]')
    driver.execute_script("arguments[0].click();",s)
    
    # Inputting the Stock Code in the Search Bar
    driver.find_element(By.XPATH, '//*[@id="newnav-search-input"]').send_keys(stock_code)
    
    # Getting the Link in the appeared Search Results
    lnks = driver.find_element(By.ID,'url')
    links=lnks.get_attribute('href')
    return links

def convert_date_string_to_datetime(date_str):
    date_format = "%d %b %Y"
    
    try:
        date_obj = datetime.strptime(date_str, date_format)
        return date_obj
    except ValueError:
        return None


# Define a function to scrape dividend information for a given stock code
def scrape_dividend_info(stock_code, start_date, end_date):
    status = ""
    try:
        # Create an empty dataframe to store dividend information
        div_info_final = pd.DataFrame()
        
        url = 'https://www.klsescreener.com/v2/stocks/view/' + stock_code
        driverdiv.get(url) 
        content = driverdiv.page_source
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
            div_info2['EX Date'] = pd.to_datetime(div_info2['EX Date'])
            div_info2['Financial Year'] = pd.to_datetime(div_info2['Financial Year'])
            div_info2['EX Date'] = pd.to_datetime(div_info2['EX Date'].dt.strftime('%Y-%m-%d'))

            # Filter data between two dates    
            filtered_df = div_info2.loc[(div_info2['EX Date'] > pd.to_datetime(start_date))
                                        & (div_info2['EX Date'] < pd.to_datetime(end_date))]
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

def assess_and_update_class(liststock):
    # Iterate through the list elements
    for i in range(4, len(liststock)+1):
        current_row = liststock[i-1]
        previous_rows = liststock[i - 4:i]  # Get the previous 4 quarters, including the current one

        # Check if the most recent date's class is 'A'
        if current_row['rClass'] == 'A':
            # Calculate the mean value of the previous 4 quarters' ratios
            avg_ratios = {
                'rEPS': sum(row['rEPS'] for row in previous_rows) / 4,
                'rPE': sum(row['rPE'] for row in previous_rows) / 4,
                'rDY': sum(row['rDY'] for row in previous_rows) / 4
            }
            print(avg_ratios['rEPS'])
            # Check if the average ratios meet your criteria
            if avg_ratios['rEPS'] > 0.1 and avg_ratios['rPE'] < 10.0 and avg_ratios['rDY'] > 0.02:
                # Update the class to 'S'
                current_row['rClass'] = 'S'

    return liststock


# update.py
def get_data(latest_dates, latest_quarter_df):
    
    # Define the end date (current day)
    end_date = datetime.today().strftime('%Y-%m-%d')   # Replace with the current date in 'YYYY-MM-DD' format

    combined_data = []  # To store successful data
    dividend_info_list = []
    results_df = pd.DataFrame(columns=["date", "revenue"])
    error_symbols = []  # To store symbols with errors
    calculated_resulting_list = []
    resulting_df = pd.DataFrame(columns=['stock_code', 'rEPS', 'rROE', 'rOM', 'rPR', 'rFCF', 'rDate'])

    global driverdiv
    global driver
    global driver2
    global driver3

    # Connect/open the Chrome webdriver
    driverdiv = webdriver.Chrome()
    driverdiv.implicitly_wait(20)
    driver = webdriver.Chrome()
    driver.implicitly_wait(20)
    driver2 = webdriver.Chrome()
    driver2.implicitly_wait(20)
    driver3 = webdriver.Chrome()
    driver3.implicitly_wait(20)


# Loop through each stock symbol and retrieve its historical data
    for row in latest_dates:
        symbol = row.stock_code
        latest_price_date = row.latest_price_date
        latest_dividend_date = row.latest_dividend_date
        latest_quarter_date = row.latest_quarter_date
        
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

        try:
            url_base=get_link(symbol) # Exclude ".KL for Bursa Marketplace Search Function"
            url = url_base + '/financials_IS_Qt'  # Append the desired subpage to the URL
            url2 = url_base + '/financials_BS_Qt'
            url3 = url_base + '/financials_CF_Qt'
            driver.get(url)
            driver2.get(url2)
            driver3.get(url3)
            content = driver.page_source
            content2 = driver2.page_source
            content3 = driver3.page_source
            soup = bs(content, features="lxml")
            soup2 = bs(content2, features="lxml")
            soup3 = bs(content3, features="lxml")

            time.sleep(2)

            # Initialize the row dictionary to store the data
            row2 = {}

            # Finding the Element to format the date
            first_sibling = driver.find_element(By.XPATH, "//div[text()='MYR (MILLION)']")
            first_sibling_year = driver.find_element(By.XPATH, "//div[contains(@class, 'tb_cell tb_metr')]")

            # Find the element with the Financial details span text
            try:
                revenue_prev_element = driver.find_element(By.XPATH, "//div[span='Total Revenue']")
                operating_income_prev_element = driver.find_element(By.XPATH, "//div[span='Operating Income']")
            except Exception as e:
                print(f"Revenue or Operating Income not found, stock code {symbol} is a bank. Proceed to scrape Net Interest Income and Total Earning Assets")
                revenue_prev_element = driver2.find_element(By.XPATH, "//div[span='Other Earning Assets, Total']")
                operating_income_prev_element = driver.find_element(By.XPATH, "//div[span='Net Interest Income']")
            preferred_dividends_prev_element = driver.find_element(By.XPATH, "//div[span='Preferred Dividends']")
            net_income_prev_element = driver.find_element(By.XPATH, "//div[span='Net Income']")
            gross_dividend_prev_element = driver.find_element(By.XPATH, "//div[span='Gross Dividends - Common Stock']")
            total_equity_prev_element = driver2.find_element(By.XPATH, "//div[span='Total Equity']")
            shares_outstanding_prev_element = driver2.find_element(By.XPATH, "//div[span='Total Common Shares Outstanding']")
            operating_cf_prev_element = driver3.find_element(By.XPATH, "//div[span='Cash from Operating Activities']")
            capital_expenditures_prev_element = driver3.find_element(By.XPATH, "//div[span='Capital Expenditures']")
            
            
            # Iterate through the next 4 siblings to get the latest 4 quarter dates
            quarter_dates = []

            for i in range(8):
                try:
                    quarter_date = first_sibling.find_element(By.XPATH, "following-sibling::div")
                    year = first_sibling_year.find_element(By.XPATH, "following-sibling::div")
                except Exception as e:
                    print(f"Stock code {symbol} does not have up to 8 quarterly reports at this time, proceeding with {i} quarters of available data.")
                    break  # Add this line to break out of the loop
                if not year.text.strip():
                    if previous_year:
                        current_date = quarter_date.text + " " + previous_year.text
                else:
                    current_date = quarter_date.text + " " + year.text
                    previous_year = year  # Update the previous_year

                date_obj = convert_date_string_to_datetime(current_date).date()
                print(f"Latest Quarter Date in Database {latest_quarter_date}")
                print(f"Latest Quarter Date found in Bursa {date_obj}")
                if latest_quarter_date == date_obj:
                    print("Dates match")
                    break

                revenue_element = revenue_prev_element.find_element(By.XPATH, "following-sibling::div")
                operating_income_element = operating_income_prev_element.find_element(By.XPATH, "following-sibling::div")
                preferred_dividends_element = preferred_dividends_prev_element.find_element(By.XPATH, "following-sibling::div")
                net_income_element = net_income_prev_element.find_element(By.XPATH, "following-sibling::div")
                gross_dividend_element = gross_dividend_prev_element.find_element(By.XPATH, "following-sibling::div")
                total_equity_element = total_equity_prev_element.find_element(By.XPATH, "following-sibling::div")
                shares_outstanding_element = shares_outstanding_prev_element.find_element(By.XPATH, "following-sibling::div")
                operating_cf_element = operating_cf_prev_element.find_element(By.XPATH, "following-sibling::div")
                capital_expenditures_element = capital_expenditures_prev_element.find_element(By.XPATH, "following-sibling::div")
                
                row2["date"] = date_obj
                row2["revenue"] = revenue_element.text
                row2["preferredDividends"] = preferred_dividends_element.text
                row2["operatingIncome"] = operating_income_element.text
                row2["netIncome"] = net_income_element.text
                row2["grossDividend"] = gross_dividend_element.text
                row2["totalEquity"] = total_equity_element.text
                row2["sharesOutstanding"] = shares_outstanding_element.text
                row2["operatingCashFlow"] = operating_cf_element.text
                row2["capitalExpenditures"] = abs(float(capital_expenditures_element.text))
                row2["stock_code"] = symbol
                if not row2["preferredDividends"].replace('.', '', 1).isdigit():
                    row2["preferredDividends"] = 0.0
                else:
                    row2["preferredDividends"] = float(row2["preferredDividends"])

                first_sibling_year = year
                first_sibling = quarter_date
                revenue_prev_element = revenue_element
                preferred_dividends_prev_element = preferred_dividends_element
                operating_income_prev_element = operating_income_element
                net_income_prev_element = net_income_element
                gross_dividend_prev_element = gross_dividend_element
                total_equity_prev_element = total_equity_element
                shares_outstanding_prev_element = shares_outstanding_element
                operating_cf_prev_element = operating_cf_element
                capital_expenditures_prev_element = capital_expenditures_element
                
                # Append the row to the results DataFrame

                results_df = results_df.append(row2, ignore_index=True)
                filtered_df = latest_quarter_df[latest_quarter_df['stock_code'] == symbol]
                filtered_df = filtered_df.append(row2, ignore_index = True)
                print("Results DF")
                print(results_df)
                print("\n")
                print("Latest Quarter DF")
                print(filtered_df)
                break

                results_df['stock_code'] = results_df['stock_code'].astype(str)
                results_df['Date'] = pd.to_datetime(results_df['Date'])
                results_df = results_df.round(3)
                latest_quarter_df['stock_code'] = latest_quarter_df['stock_code'].astype(str)
                latest_quarter_df['Date'] = pd.to_datetime(latest_quarter_df['Date'])
                latest_quarter_df = latest_quarter_df.round(3)

                calculated_stock_df = pd.DataFrame()
                calculated_stock_list = []
                calculated_data = {}

                filtered_df = latest_quarter_df[latest_quarter_df['stock_code'] == stock_code]
                filtered_df = filtered_df.sort_values(by='Date', ascending=True)
                filtered_df = filtered_df.reset_index(drop=True)
                print(f"Stock Code: {stock_code}")

                loop_start = 4 if len(filtered_df) == 4 else 5

                for i in range(loop_start, len(filtered_df)+1):
                    # Calculate the average of the last four quarters' capital expenditures
                    average_shares = sum(filtered_df['sharesOutstanding'].iloc[i - 4:i]) / 4
                    average_equity = sum(filtered_df['totalEquity'].iloc[i - 4:i]) / 4
                    
                    sum_income = sum(filtered_df['netIncome'].iloc[i - 4:i])
                    sum_revenue = sum(filtered_df['revenue'].iloc[i - 4:i])
                    sum_operating_income = sum(filtered_df['operatingIncome'].iloc[i - 4:i])
                    sum_gross_dividend = sum(filtered_df['grossDividend'].iloc[i - 4:i])
                    sum_operating_cash_flow = sum(filtered_df['operatingCashFlow'].iloc[i - 4:i])
                    sum_capital_expenditures = sum(filtered_df['capitalExpenditures'].iloc[i - 4:i])
                    
                    # Calculate rPE and rDY
                    rEPS = sum_income / average_shares if average_shares != 0 else 0
                    rDPS = sum_gross_dividend / average_shares if average_shares != 0 else 0
                    stock_code = stock_code  # You may omit this line if stock_code doesn't change
                    
                    rPE = 0  # Initialize rPE
                    rDY = 0  # Initialize rDY
                    
                    try:
                        # print(f"Current i {i}")
                        last_recorded_date = historical_prices_df[
                            (historical_prices_df['stock_code'] == stock_code) &
                            (historical_prices_df['MonthPeriod'] == filtered_df['Date'].iloc[i-1].to_period('M'))
                        ].sort_values(by='Date').iloc[-1]['Date']
                        # print(f"Last Date: {last_recorded_date} \n")
                        
                        closing_price = historical_prices_df[
                            (historical_prices_df['stock_code'] == stock_code) &
                            (historical_prices_df['Date'] == last_recorded_date)
                        ]['Close'].values[0]
                        # print(f"Closing Price: {closing_price} \n")
                        # Rest of your code that depends on last_recorded_date and closing_price
                    except IndexError:
                        print("IndexError: Single positional indexer is out of bounds.")
                        break  # This line will exit the loop when an IndexError is encountered

                    # Calculate rPE and rDY
                    rPE = (closing_price / rEPS) 
                    rDY = (rDPS / closing_price)
                    
                    # Create a dictionary with the calculated values
                    calculated_data = {
                        'stock_code': stock_code,
                        'rEPS': rEPS,
                        'rDPS': rDPS,
                        'rROE': sum_income / average_equity if average_equity != 0 else 0,
                        'rOM': sum_operating_income / sum_revenue if sum_revenue != 0 else 0,
                        'rPR': rDPS / rEPS if rEPS != 0 else 0,
                        'rFCF': (sum_operating_cash_flow - sum_capital_expenditures),
                        'rDate': filtered_df['Date'].iloc[i-1],
                        'rPE': rPE,
                        'rDY': rDY
                    }
                    # Calculate the 'rClass' based on the choices
                    dividend_condition = (calculated_data['rDY'] >= 0.02) & (calculated_data['rPR'] >= 0.1) & (calculated_data['rPR'] <= 0.75)
                    foundation_condition = (calculated_data['rOM'] >= 0.1) & (calculated_data['rFCF'] >= 0) & (calculated_data['rPE'] <= 10) & (calculated_data['rROE'] >= 0.20) & (calculated_data['rEPS'] >= 0.1)

                    if dividend_condition & foundation_condition:
                        calculated_data['rClass'] = 'A'
                        a_class = True
                    elif foundation_condition:
                        calculated_data['rClass'] = 'B'
                    elif dividend_condition:
                        calculated_data['rClass'] = 'C'
                    else:
                        calculated_data['rClass'] = 'D'
                        
                    # Append the dictionary to the list
                    calculated_stock_list.append(calculated_data)
                    calculated_stock_list = assess_and_update_class(calculated_stock_list)
                    calculated_resulting_list.append(calculated_data)
                    
                # Convert the list of dictionaries to a DataFrame
                resulting_stock_df = pd.DataFrame(calculated_stock_list)

                # Display the DataFrame in a nice table format in a Jupyter Notebook
                print(resulting_stock_df)
                print("\n")

            # Convert the list of dictionaries to a DataFrame
            resulting_df = pd.DataFrame(calculated_resulting_list)
                


        except Exception as e:
            print(f"Error fetching data for {symbol}: {str(e)}")

    # After the loop, concatenate all DataFrames into a single DataFrame
    price_df = pd.concat(combined_data)
    dividend_df = pd.concat(dividend_info_list)
    print(results_df.head())
    print(dividend_df.head())

    columns_to_remove_df = ["Financial Year", "Subject", "Indicator", "Year", "Status", "Unnamed: 7"]
    dividend_df = dividend_df.drop(columns=columns_to_remove_df)
    # print(price_df.head())

    # The 'final_df' DataFrame contains the combined historical data for all successful stock symbols
