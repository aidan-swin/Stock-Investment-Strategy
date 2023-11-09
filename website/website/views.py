from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for, Response
from flask_login import  login_required,  current_user
from .models import CompanyInfo, User, Stocks, Ratiottm, Watchlist, Price, Dividend, Quarter, Portfolio
from . import db
import json
import pickle
import numpy as np
import pandas as pd
import csv
import shap
import datetime
from sqlalchemy.sql import func, desc, literal , join
from sqlalchemy import and_
from sklearn.preprocessing import StandardScaler
from sklearn.inspection import permutation_importance
from .custom_shap import TreeExplainer
from collections import defaultdict
from datetime import date, timedelta, datetime
from sqlalchemy.orm import aliased
from .update import get_data


views = Blueprint('views', __name__)

@views.route('/', methods=['GET', 'POST'])
def home():
    # Select all records from the Stocks table
    all_stocks = Stocks.query.all()
    return render_template("home.html", user=current_user, company=all_stocks)


@views.route('/watchlist', methods=['GET', 'POST'])
@login_required
def watchlist():
    # Get the current user's ID
    current_user_id = current_user.id

    # Filter the Watchlist table to get the stocks in the watchlist for the current user
    user_watchlist = Watchlist.query.filter_by(user_id=current_user_id).all()
        # Create a list of stock codes for the user's watchlist
    user_watchlist_stock_codes = [item.stock_code for item in user_watchlist]

    # Select the stocks in the watchlist for the current user from the Stocks table
    user_watchlist_stocks = Stocks.query.filter(Stocks.stock_code.in_(user_watchlist_stock_codes)).all()
    if request.method =='POST':
        filename = 'companyinfo.csv'
        headers = [' ID',
        ' companyname',
        ' equity_ratio', 
        ' importance_equity_ratio', 
        ' liabilities_coverage',
        ' importance_liabilities_coverage',
        ' operating_profit_margin_to_financial_expense', 
        ' importance_operating_profit_margin_to_financial_expense', 
        ' working_capital_to_fixed_assets', 
        ' importance_working_capital_to_fixed_assets', 
        ' current_liabilities_by_365_by_cost_of_products_sold', 
        ' importance_current_liabilities_by_365_by_cost_of_products_sold', 
        ' operating_expenses_to_total_liabilities', 
        ' importance_operating_expenses_to_total_liabilities', 
        ' current_assets_without_inventories_to_liabilities', 
        ' importance_current_assets_without_inventories_to_liabilities', 
        ' liability_to_operating_profit_ratio_per_day', 
        ' importance_liability_to_operating_profit_ratio_per_day',
        ' net_profit_to_inventory', 
        ' importance_net_profit_to_inventory',
        ' assets_without_inventories_and_short_term_liabilities_to_sales_without_gross_profit_and_depreciation',
        ' importance_assets_without_inventories_and_short_term_liabilities_to_sales_without_gross_profit_and_depreciation',
        ' forecast_period',
        ' Bankrupt',
        ' Risk']
        with open(filename, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(headers)
            for item in all_stocks:
                writer.writerow([item.id, 
                                item.companyname, 
                                item.equity_ratio, 
                                item.equity_ratio_i,
                                item.liabilities_coverage, 
                                item.liabilities_coverage_i, 
                                item.operating_profit_margin_to_financial_expense, 
                                item.operating_profit_margin_to_financial_expense_i, 
                                item.working_capital_to_fixed_assets, 
                                item.working_capital_to_fixed_assets_i, 
                                item.current_liabilities_by_365_by_cost_of_products_sold,
                                item.current_liabilities_by_365_by_cost_of_products_sold_i,
                                item.operating_expenses_to_total_liabilities, 
                                item.operating_expenses_to_total_liabilities_i, 
                                item.current_assets_without_inventories_to_liabilities, 
                                item.current_assets_without_inventories_to_liabilities_i, 
                                item.liability_to_operating_profit_ratio_per_day, 
                                item.liability_to_operating_profit_ratio_per_day_i, 
                                item.net_profit_to_inventory, 
                                item.net_profit_to_inventory_i, 
                                item.assets_without_inventories_and_short_term_liabilities_to_sales_without_gross_profit_and_depreciation, 
                                item.assets_without_inventories_and_short_term_liabilities_to_sales_without_gross_profit_and_depreciation_i, 
                                item.forecast_period,
                                item.Bankrupt,
                                item.Risk])
            return Response(open(filename, 'r'), mimetype='text/csv', headers={"Content-Disposition":"attachment;filename=my_table.csv"})
    return render_template("watchlist.html", user=current_user, company=user_watchlist_stocks)

# Function to get the first day (Monday) of a week based on year and week number
def first_day_of_week(year, week_number):
    d = datetime.fromisocalendar(year, week_number, 1)
    if d.weekday() != 0:
        # Move back to the previous Monday if not already Monday
        d -= timedelta(days=d.weekday())
    
    # Subtract one day to get the date before and format it
    return (d - timedelta(days=1)).strftime('%Y-%m-%d')

@views.route('/detail/<string:id>')
def detail(id):
    company = Stocks.query.get_or_404(id)
        
    # Get the latest date ratio record for the stock_code
    ratios = (
        db.session.query(Ratiottm)
        .filter_by(stock_code=company.stock_code)
        .order_by(desc(Ratiottm.rDate))
        .first()
    )   

      # Get the latest date ratio record for the stock_code
    pastratios = (
        db.session.query(Ratiottm)
        .filter_by(stock_code=company.stock_code)
        .order_by(desc(Ratiottm.rDate))
        .all()
    )
    print(f"Past Ratio Stock Code {pastratios[0].stock_code}")

    # Calculate the average of the first 3 records for each ratio column and round to 3 decimal places
    average_eps = round(sum(r.rEPS for r in pastratios[:3]) / 3, 3)
    average_pe = round(sum(r.rPE for r in pastratios[:3]) / 3, 3)
    average_roe = round(sum(r.rROE for r in pastratios[:3]) / 3, 3)
    average_om = round(sum(r.rOM for r in pastratios[:3]) / 3, 3)
    average_dy = round(sum(r.rDY for r in pastratios[:3]) / 3, 3)
    average_pr = round(sum(r.rPR for r in pastratios[:3]) / 3, 3)
    average_class = 'Forecast'  # You can set this as 'Forecast' or any other value you prefer.



    # Create a dictionary with the averages
    forecast_data = {
        'rDate': "Forecast",
        'rEPS': average_eps,
        'rPE': average_pe,
        'rROE': average_roe,
        'rOM': average_om,
        'rDY': average_dy,
        'rPR': average_pr,
        'rClass': average_class,
    }
    pastratios.insert(0, forecast_data)
    dividend_records = (
    db.session.query(Dividend)
    .filter_by(stock_code=company.stock_code)
    .all()  # Execute the query and retrieve all matching records
)

    # Check if the stock is in the user's watchlist
    is_in_watchlist = False  # Initialize as False
    if current_user.is_authenticated:
        watchlist_entry = Watchlist.query.filter_by(stock_code=company.stock_code, user_id=current_user.id).first()
        if watchlist_entry:
            is_in_watchlist = True
    
    prices = (
        db.session.query(Price)
        .filter_by(stock_code=company.stock_code)
        .all()
    )
    print(prices[0].stock_code)


        # Create a dictionary to store aggregated data
    monthly_averages = defaultdict(list)

    # Iterate through the Price records and group by month and year
    for price in prices:
        date = price.Date  # Assuming the date is in a suitable format
        month_year = date.strftime('%Y-%m')  # Extract the month and year (e.g., 'YYYY-MM')
        close_price = price.Close

        if month_year not in monthly_averages:
            monthly_averages[month_year] = []

        monthly_averages[month_year].append(close_price)


    # Calculate the average Close price for each month
    average_monthly_data = [
    {'x': month_year, 'y': sum(prices) / len(prices)}
    for month_year, prices in monthly_averages.items()
]


    # Retrieve the 14 latest records with the Date and Close columns
    latest_14_prices = (
        db.session.query(Price.Date, Price.Close)
        .filter_by(stock_code=company.stock_code)
        .order_by(Price.Date.desc())  # Sort by Date in descending order
        .limit(20)
        .all()
    )

    # Convert the result into a list of dictionaries
    price_14 = [
        {'x': price.Date.strftime('%Y-%m-%d'), 'y': price.Close}
        for price in latest_14_prices
    ]
    # Calculate the date for 5 weeks ago from today
    five_weeks_ago = datetime.now() - timedelta(weeks=20)

    # Retrieve the last five weeks of records with the Date and Close columns
    last_five_weeks_prices = (
        db.session.query(Price.Date, Price.Close)
        .filter_by(stock_code=company.stock_code)
        .filter(Price.Date >= five_weeks_ago)
        .all()
    )

    # Group the data by week and calculate the weekly averages
    weekly_averages = defaultdict(list)

    for price in last_five_weeks_prices:
        date = price.Date
        year, week, _ = date.isocalendar()
        week_key = f'{year}-{week}'

        weekly_averages[week_key].append(price.Close)

    # Calculate the average Close price for each week with the first day of the week as 'x'
    weekly_average_data = [
        {'x': first_day_of_week(int(week_key.split('-')[0]), int(week_key.split('-')[1])), 'y': sum(prices) / len(prices)}
        for week_key, prices in weekly_averages.items()
    ]
    print(price_14)

    # Retrieve the first 8 records with rPE and rDate columns
    first_8_ratios = (
        db.session.query(Ratiottm.rDate, Ratiottm.rPE, Ratiottm.rEPS, Ratiottm.rROE, Ratiottm.rOM, Ratiottm.rDY, Ratiottm.rPR, Ratiottm.rFCF)
        .filter_by(stock_code=company.stock_code)
        .order_by(Ratiottm.rDate)
        .limit(8)
        .all()
    )

    # Convert the result into a list of dictionaries with 'x' and 'y' keys
    rEPS_data = [
    {'x': ratio.rDate.strftime('%Y-%m-%d'), 'y': ratio.rEPS}
    for ratio in first_8_ratios
    ]
    rPE_data = [
        {'x': ratio.rDate.strftime('%Y-%m-%d'), 'y': ratio.rPE}
        for ratio in first_8_ratios
    ]
    rROE_data = [
        {'x': ratio.rDate.strftime('%Y-%m-%d'), 'y': ratio.rROE}
        for ratio in first_8_ratios
    ]
    rOM_data = [
        {'x': ratio.rDate.strftime('%Y-%m-%d'), 'y': ratio.rOM}
        for ratio in first_8_ratios
    ]
    rDY_data = [
        {'x': ratio.rDate.strftime('%Y-%m-%d'), 'y': ratio.rDY}
        for ratio in first_8_ratios
    ]
    rPR_data = [
        {'x': ratio.rDate.strftime('%Y-%m-%d'), 'y': ratio.rPR}
        for ratio in first_8_ratios
    ]
    rFCF_data = [
        {'x': ratio.rDate.strftime('%Y-%m-%d'), 'y': ratio.rFCF}
        for ratio in first_8_ratios
    ]
    # Retrieve the first 8 records with the dExDate and dAmount columns
    first_8_dividends = (
        db.session.query(Dividend.dExDate, Dividend.dAmount)
        .filter_by(stock_code=company.stock_code)
        .order_by(Dividend.dExDate)
        .limit(8)
        .all()
    )

    # Convert the result into a list of dictionaries with 'x' and 'y' keys
    dividend_data = [
        {'x': dividend.dExDate.strftime('%Y-%m-%d'), 'y': dividend.dAmount}
        for dividend in first_8_dividends
    ]

    if current_user.is_authenticated:
    # Check if the user has 5 or more entries in their watchlist
        watchlist_count = db.session.query(Watchlist).filter_by(user_id=current_user.id).count()
    else:
        watchlist_count = 5

        
    return render_template('detail.html', user=current_user, company=company, ratios=ratios, pastratios=pastratios, price_14=price_14, dividend_records=dividend_records,is_in_watchlist=is_in_watchlist, prices=prices, average_monthly_data = average_monthly_data,weekly_average_data=weekly_average_data, rEPS_data=rEPS_data,rPE_data=rPE_data,rROE_data=rROE_data,rOM_data=rOM_data, rDY_data=rDY_data, rPR_data=rPR_data, rFCF_data=rFCF_data, dividend_data=dividend_data, watchlist_count=watchlist_count)

@views.route('/add_to_watchlist/<string:id>', methods=['POST'])
@login_required
def add_to_watchlist(id):
    company = Stocks.query.get_or_404(id)

    # Check if the entry already exists in the Watchlist table
    watchlist_entry = Watchlist.query.filter_by(stock_code=company.stock_code, user_id=current_user.id).first()

    if watchlist_entry:
        # If the entry exists, remove it from the watchlist
        db.session.delete(watchlist_entry)
        db.session.commit()
        flash('Removed from Watchlist', 'success')
    else:
        # If the entry doesn't exist, add it to the watchlist
        new_watchlist_entry = Watchlist(stock_code=company.stock_code, user_id=current_user.id)
        db.session.add(new_watchlist_entry)
        db.session.commit()
        flash('Added to Watchlist', 'success')

    return redirect(url_for('views.detail', id=id))


@views.route('/delete_item/<int:id>', methods=['POST'])
@login_required
def delete_item(id):
    companyinfo_to_delete = CompanyInfo.query.get_or_404(id)
    db.session.delete(companyinfo_to_delete)
    db.session.commit()
    flash('Company Info has been deleted!', 'success')
    return redirect(url_for('views.companyinfo'))

@views.route('/backtest', methods=['GET', 'POST'])
@login_required
def backtest():
    # Retrieve the list of stock codes from the user's watchlist
    watchlist_stocks = Watchlist.query.filter_by(user_id=current_user.id).all()
    stock_codes = [entry.stock for entry in watchlist_stocks]

    # stock_codes = Stocks.query.all()

    max_date = date.today() - timedelta(days=1) # Get the current date as the max date for the HTML date input

    if request.method == 'POST':
        stock_code = request.form.get('stock')
        print(stock_code)
        unit_quantity = float(request.form.get('unit_quantity'))
        purchase_date = datetime.strptime(request.form.get('purchase_date'), '%Y-%m-%d').date()

        # Calculate the end date for the query (current_date - 1 day)
        end_date = date.today() - timedelta(days=1)

        # Query the Price table for records that match the stock_code and date range
        prices = (
            Price.query
            .filter(Price.stock_code == stock_code)
            .filter(Price.Date >= purchase_date, Price.Date <= end_date)
            .order_by(Price.Date)  # Order the results by Date in ascending order
            .all()
        )

        # Now you can safely access the latest date, which will be the last item in the list
        if prices:
            latest_date = prices[-1].Date
            purchase_date = prices[0].Date

        # Access the first and last record's Close column
        purchase_price = round(prices[0].Close * unit_quantity, 3)
        latest_price = round(prices[-1].Close * unit_quantity, 3)

        price_diff = round(latest_price - purchase_price, 3)
        price_perc = round(price_diff / purchase_price * 100, 3)

        print("Purchase Date: " + str(purchase_date) + " Latest Date " + str(latest_date))
        print("Purchase Price: " + str(purchase_price) + " Latest Price " + str(latest_price))
        print("Price Difference: " + str(price_diff) + " Price Percentage " + str(price_perc))

        dividends = (
            Dividend.query
            .filter(Dividend.stock_code == stock_code)
            .filter(Dividend.dExDate >= purchase_date, Dividend.dExDate <= latest_date)
            .all()
        )

        # Calculate the dividend amount
        dividend_amount = sum(dividend.dAmount for dividend in dividends) * unit_quantity



        # Calculate the dividend yield
        dividend_yield = dividend_amount / purchase_price

        print("Dividend Amount: " + str(dividend_amount))
        print("Dividend Yield: " + str(dividend_yield))

        # Now, first_record_date contains the date from the first record

        # print(prices)
        # Now 'prices' contains the Price records that match the criteria
        new_portfolio = Portfolio(stock_code=stock_code, unitQuantity=unit_quantity, purchaseDate=purchase_date,user_id=current_user.id)
        db.session.add(new_portfolio)
        db.session.commit()
    

        flash('Backtest submitted successfully!', 'success')
        return redirect(url_for('views.backtest'))
    
    # Query the Portfolio records for the current user
        # Query the Portfolio records and join with Stocks to get stock_name
   # Query the Portfolio records for the current user, including the stock_name
    portfolio_results = db.session.query(Portfolio, Stocks.stock_name).join(Stocks).filter(Portfolio.user_id == current_user.id).all()
        # Print the query results
    for result in portfolio_results:
        print(result)  # Print the entire result tuple
    
        # Process each stock in the portfolio
    results = []  # Store the results for each stock
    for portfolio, stock_name in portfolio_results:
        stock_code = portfolio.stock_code
        unit_quantity = portfolio.unitQuantity
        purchase_date = portfolio.purchaseDate

        # Calculate the end date for the query (current_date - 1 day)
        end_date = date.today() - timedelta(days=1)

        # Query the Price table for records that match the stock_code and date range
        prices = (
            Price.query
            .filter(Price.stock_code == stock_code)
            .filter(Price.Date >= purchase_date, Price.Date <= end_date)
            .order_by(Price.Date)  # Order the results by Date in ascending order
            .all()
        )

        # Now you can safely access the latest date, which will be the last item in the list
        if prices:
            latest_date = prices[-1].Date
            purchase_date = prices[0].Date

        # Access the first and last record's Close column
        purchase_price = round(prices[0].Close * unit_quantity, 3)
        latest_price = round(prices[-1].Close * unit_quantity, 3)

        price_diff = round(latest_price - purchase_price, 3)
        price_perc = round(price_diff / purchase_price * 100, 3)

        dividends = (
            Dividend.query
            .filter(Dividend.stock_code == stock_code)
            .filter(Dividend.dExDate >= purchase_date, Dividend.dExDate <= latest_date)
            .all()
        )

        # Calculate the dividend amount
        dividend_amount = sum(dividend.dAmount for dividend in dividends) * unit_quantity

        # Calculate the dividend yield
        dividend_yield = dividend_amount / purchase_price

        # Store the results for this stock
        result = {
            "stock_name": stock_name,
            "stock_code": stock_code,
            "purchase_date": purchase_date,
            "latest_date": latest_date,
            "purchase_price": purchase_price,
            "latest_price": latest_price,
            "price_diff": price_diff,
            "price_perc": price_perc,
            "dividend_amount": dividend_amount,
            "dividend_yield": dividend_yield
        }
        results.append(result)

    # Print or return the results, depending on your needs
    for result in results:
        print(result)

    return render_template('backtest.html', user=current_user, stocks=stock_codes, max_date=max_date, portfolio_results = portfolio_results)

# Route to upload CSV file
@views.route('/forecast', methods=['GET', 'POST'])
@login_required
def upload_file():
    if request.method == 'POST':
        # Save the uploaded file
        file = request.files['file']
        filename = file.filename
        file.save(filename)

        # Read the CSV file into a Pandas dataframe
        df = pd.read_csv(filename)

        with open('D:/VisualStudioCode/BRS_Official/BRS/random_forest_model.pkl', 'rb') as f:
            rf = pickle.load(f)
        
        with open('D:/VisualStudioCode/BRS_Official/BRS/scaler.pkl', 'rb') as f:
            scaler = pickle.load(f)
        
        counter=0
        for index, row in df.iterrows():
            input_values = [row[' equity_ratio'], 
                    row[' liabilities_coverage'], 
                    row[' operating_profit_margin_to_financial_expense'], 
                    row[' working_capital_to_fixed_assets'], 
                    row[' current_liabilities_by_365_by_cost_of_products_sold'], 
                    row[' operating_expenses_to_total_liabilities'], 
                    row[' current_assets_without_inventories_to_liabilities'], 
                    row[' liability_to_operating_profit_ratio_per_day'], 
                    row[' net_profit_to_inventory'], 
                    row[' assets_without_inventories_and_short_term_liabilities_to_sales_without_gross_profit_and_depreciation'],
                    row[' forecast_period']]
            
            # Scale the input values
            input_values_scaled = scaler.transform([input_values])

            # Use the trained Random Forest model for prediction
            prediction = rf.predict(input_values_scaled)
            
            risk=rf.predict_proba(input_values_scaled)[:, 1]
            risk=np.round(risk,2)
            print(prediction)  
            print(risk) 

             # Get the risk probability
            risk = rf.predict_proba(input_values_scaled)[:, 1]
            risk = np.round(risk, 2)

            # Create a TreeExplainer object with the trained model
            explainer = shap.TreeExplainer(rf)

            # Get the SHAP values for the specific record
            shap_values = explainer.shap_values(input_values_scaled)

            # Sum the absolute SHAP values across features for the specific record
            feature_importances = np.abs(shap_values).mean(axis=0)

            # Normalize the feature importances so that they sum up to 1
            normalized_importances = feature_importances / np.sum(feature_importances)

            # Print the normalized feature importances
            for importance in normalized_importances:
                print(f"Importance: {importance}")


           # Store the normalized importances in a 1D array to be stored in database
            importance_array = normalized_importances.flatten()

            counter += 1
            # prediction = rf.predict([[row[' Operating Gross Margin'], OperatingProfitRate=row[' Operating Profit Rate'], row[' Continuous interest rate (after tax)'], row[' Operating Expense Rate'], row[' Cash flow rate'], row[' Gross Profit to Sales'], row[' Continuous Net Profit Growth Rate'], row[' Total debt/Total net worth'], row[' Cash Turnover Rate'], row[' Current Liability to Current Assets']]])
            new_data = CompanyInfo(companyname=row[' companyname'], 
                                   equity_ratio=row[' equity_ratio'],
                                   liabilities_coverage=row[' liabilities_coverage'], 
                                   operating_profit_margin_to_financial_expense=row[' operating_profit_margin_to_financial_expense'],
                                   working_capital_to_fixed_assets=row[' working_capital_to_fixed_assets'],
                                   current_liabilities_by_365_by_cost_of_products_sold=row[' current_liabilities_by_365_by_cost_of_products_sold'], 
                                   operating_expenses_to_total_liabilities=row[' operating_expenses_to_total_liabilities'],
                                   current_assets_without_inventories_to_liabilities=row[' current_assets_without_inventories_to_liabilities'],
                                   liability_to_operating_profit_ratio_per_day=row[' liability_to_operating_profit_ratio_per_day'],
                                   net_profit_to_inventory=row[' net_profit_to_inventory'],
                                   assets_without_inventories_and_short_term_liabilities_to_sales_without_gross_profit_and_depreciation=row[' assets_without_inventories_and_short_term_liabilities_to_sales_without_gross_profit_and_depreciation'],
                                   equity_ratio_i = importance_array[0],
                                    liabilities_coverage_i = importance_array[1],
                                    operating_profit_margin_to_financial_expense_i = importance_array[2],
                                    working_capital_to_fixed_assets_i = importance_array[3],
                                    current_liabilities_by_365_by_cost_of_products_sold_i = importance_array[4],
                                    operating_expenses_to_total_liabilities_i = importance_array[5],
                                    current_assets_without_inventories_to_liabilities_i = importance_array[6],
                                    liability_to_operating_profit_ratio_per_day_i = importance_array[7],
                                    net_profit_to_inventory_i = importance_array[8],
                                    assets_without_inventories_and_short_term_liabilities_to_sales_without_gross_profit_and_depreciation_i = importance_array[9],
                                   forecast_period=row[' forecast_period'],
                                   Bankrupt=prediction, 
                                   user_id = current_user.id, 
                                   Risk=risk)
            db.session.add(new_data)
            if counter >= 1000:
                flash(f'CSV File of {counter} records reached! Only the first {counter} records are uploaded.', category='Success')
                break
        
            
        db.session.commit()
        flash(f'CSV File Uploaded! {counter} records are uploaded.', category='success')
        results=CompanyInfo.query.all()

        # Return a message indicating success
        return render_template('forecast.html',user=current_user,results=results)

    # Render the upload form if GET request
    return render_template('add_csv.html',user=current_user)


@views.route('/add_csv')
@login_required
def add_csv():
    return render_template("add_csv.html", user=current_user)

# Route to download the template file
@views.route('/download_template')
@login_required
def download_template():
    filename = 'companyinfo_template.csv'
    headers = [
        'ID',
        'companyname',
        'equity_ratio',
        'importance_equity_ratio',
        'liabilities_coverage',
        'importance_liabilities_coverage',
        'operating_profit_margin_to_financial_expense',
        'importance_operating_profit_margin_to_financial_expense',
        'working_capital_to_fixed_assets',
        'importance_working_capital_to_fixed_assets',
        'current_liabilities_by_365_by_cost_of_products_sold',
        'importance_current_liabilities_by_365_by_cost_of_products_sold',
        'operating_expenses_to_total_liabilities',
        'importance_operating_expenses_to_total_liabilities',
        'current_assets_without_inventories_to_liabilities',
        'importance_current_assets_without_inventories_to_liabilities',
        'liability_to_operating_profit_ratio_per_day',
        'importance_liability_to_operating_profit_ratio_per_day',
        'net_profit_to_inventory',
        'importance_net_profit_to_inventory',
        'assets_without_inventories_and_short_term_liabilities_to_sales_without_gross_profit_and_depreciation',
        'importance_assets_without_inventories_and_short_term_liabilities_to_sales_without_gross_profit_and_depreciation',
        'forecast_period',
        'Bankrupt',
        'Risk'
    ]

    # Create the template file and write the headers
    with open(filename, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(headers)

    return Response(open(filename, 'r'), mimetype='text/csv', headers={"Content-Disposition":"attachment;filename=my_table.csv"})

@views.route('/information')
@login_required
def show_information():
    return render_template('information.html', user=current_user)

@views.route('/update-stocks', methods=['GET', 'POST'])
def update_stock():
    if request.method =='POST':
        flash('CSV File of records reached! Only the first records are uploaded.', category='Success')
        # Subquery to get the latest date for each table

        # Create aliases for the tables to simplify the query
        dividend_alias = aliased(Dividend)
        price_alias = aliased(Price)
        quarter_alias = aliased(Quarter)

        # Subquery to get the latest dates for each table
        latest_dividend_date_subquery = (
            db.session.query(
                Dividend.stock_code,
                func.max(Dividend.dExDate).label("latest_dividend_date")
            )
            .group_by(Dividend.stock_code)
            .subquery()
        )

        latest_price_date_subquery = (
            db.session.query(
                Price.stock_code,
                func.max(Price.Date).label("latest_price_date")
            )
            .group_by(Price.stock_code)
            .subquery()
        )

        latest_quarter_date_subquery = (
            db.session.query(
                Quarter.stock_code,
                func.max(Quarter.date).label("latest_quarter_date")
            )
            .group_by(Quarter.stock_code)
            .subquery()
        )

        # Join the subqueries to get the latest dates for each stock code
        latest_dates_query = (
            db.session.query(
                Stocks.stock_code,
                latest_dividend_date_subquery.c.latest_dividend_date,
                latest_price_date_subquery.c.latest_price_date,
                latest_quarter_date_subquery.c.latest_quarter_date
            )
            .outerjoin(latest_dividend_date_subquery, Stocks.stock_code == latest_dividend_date_subquery.c.stock_code)
            .outerjoin(latest_price_date_subquery, Stocks.stock_code == latest_price_date_subquery.c.stock_code)
            .outerjoin(latest_quarter_date_subquery, Stocks.stock_code == latest_quarter_date_subquery.c.stock_code)
        )

        # Execute the query
        # Execute the query and limit the result to the first 5 rows
        latest_dates = latest_dates_query.limit(5).all()
        

        # # Print or use the results as needed
        # for row in latest_dates:
        #     stock_code, latest_dividend_date, latest_price_date, latest_quarter_date = row
        #     print(f"Stock Code: {stock_code}")
        #     print(f"Latest Dividend Date: {latest_dividend_date}")
        #     print(f"Latest Price Date: {latest_price_date}")
        #     print(f"Latest Quarter Date: {latest_quarter_date}")

        ranked_quarter_subquery = (
        db.session.query(
            quarter_alias.stock_code,
            quarter_alias.date,
            func.row_number().over(
                partition_by=quarter_alias.stock_code,
                order_by=quarter_alias.date.desc()
            ).label("row_num")
        )
        .subquery()
         )

        # Query to get the 4 latest records for each stock code
        latest_quarter_query = (
            db.session.query(quarter_alias)
            .join(
                ranked_quarter_subquery,
                and_(
                    quarter_alias.stock_code == ranked_quarter_subquery.c.stock_code,
                    quarter_alias.date == ranked_quarter_subquery.c.date
                )
            )
            .filter(ranked_quarter_subquery.c.row_num <= 3)
        )

        # Execute the query to get the 3 latest records for each stock code in the Quarter table
        latest_quarter_records = latest_quarter_query.limit(80).all()

        #Convert the Quarter Object returned by the query into a List
        latest_quarter_list = [
            {
                'id': record.id,
                'date': record.date,
                'revenue': record.revenue,
                'capitalExpenditures': record.capitalExpenditures,
                'grossDividend': record.grossDividend,
                'netIncome': record.netIncome,
                'operatingCashFlow': record.operatingCashFlow,
                'operatingIncome': record.operatingIncome,
                'preferredDividends': record.preferredDividends,
                'sharesOutstanding': record.sharesOutstanding,
                'totalEquity': record.totalEquity,
                'stock_code': record.stock_code
            }
            for record in latest_quarter_records
        ]

        # Convert the list of dictionaries to a DataFrame
        latest_quarter_df = pd.DataFrame(latest_quarter_list)
        
        print(f"Latest Date data type {type(latest_dates)}")
        print(f"Latest Quarter List data type {type(latest_quarter_list)}")

        
        get_data(latest_dates, latest_quarter_df)

    return render_template("update-stocks.html", user=current_user)

@views.route('/export_csv', methods=['POST'])
def export_csv():
    data = request.form.get('table_data')
    # Parse the data and write it to a CSV file
    # You can use the `csv` module to write the data to a CSV file
    # Create a Response object to serve the CSV file as a download
    response = Response(data, content_type='text/csv')
    response.headers["Content-Disposition"] = "attachment; filename=table_data.csv"
    return response
