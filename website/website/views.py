from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for, Response
from flask_login import  login_required,  current_user
from .models import CompanyInfo, User, Stocks, Ratiottm, Watchlist, Price, Dividend, Quarter
from . import db
import json
import pickle
import numpy as np
import pandas as pd
import csv
import shap
import datetime
from sqlalchemy.sql import func, desc, literal
from sklearn.preprocessing import StandardScaler
from sklearn.inspection import permutation_importance
from .custom_shap import TreeExplainer
from collections import defaultdict
from datetime import date, timedelta, datetime
from sqlalchemy.orm import aliased
from .update import get_data


views = Blueprint('views', __name__)

@views.route('/', methods=['GET', 'POST'])
@login_required
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


@views.route('/detail/<string:id>')
@login_required
def detail(id):
    company = Stocks.query.get_or_404(id)
        
    # Get the latest date ratio record for the stock_code
    ratios = (
        db.session.query(Ratiottm)
        .filter_by(stock_code=company.stock_code)
        .order_by(desc(Ratiottm.rDate))
        .first()
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
        .order_by(Price.Date.desc())  # Order by the Date column in descending order
        .all()
    )


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
    average_monthly_data = {
        month_year: sum(prices) / len(prices)
        for month_year, prices in monthly_averages.items()
    }
    print(average_monthly_data)
        
    return render_template('detail.html', user=current_user, company=company, ratios=ratios, is_in_watchlist=is_in_watchlist, prices=prices, average_monthly_data = average_monthly_data)

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
        unit_quantity = request.form.get('unit_quantity')
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
        purchase_price = round(prices[0].Close, 3)
        latest_price = round(prices[-1].Close, 3)

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
        dividend_amount = sum(dividend.dAmount for dividend in dividends)

        # Calculate the dividend yield
        dividend_yield = dividend_amount / purchase_price

        print("Dividend Amount: " + str(dividend_amount))
        print("Dividend Yield: " + str(dividend_yield))

        # Now, first_record_date contains the date from the first record

        # print(prices)
        # Now 'prices' contains the Price records that match the criteria

        flash('Backtest submitted successfully!', 'success')
        return redirect(url_for('views.backtest'))

    return render_template('backtest.html', user=current_user, stocks=stock_codes, max_date=max_date)

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

        # Print or use the results as needed
        for row in latest_dates:
            stock_code, latest_dividend_date, latest_price_date, latest_quarter_date = row
            print(f"Stock Code: {stock_code}")
            print(f"Latest Dividend Date: {latest_dividend_date}")
            print(f"Latest Price Date: {latest_price_date}")
            print(f"Latest Quarter Date: {latest_quarter_date}")
        
        get_data(latest_dates)

    return render_template("update-stocks.html", user=current_user)


