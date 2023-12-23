from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for, Response
from flask_login import  login_required,  current_user
from .models import CompanyInfo, User, Stocks, Ratiottm, Watchlist, Price, Dividend, Quarter, Portfolio
from . import db
import pandas as pd
import datetime
from sqlalchemy.sql import func, desc , join
from sqlalchemy import and_
from collections import defaultdict
from datetime import date, timedelta, datetime
from sqlalchemy.orm import aliased
from .update import get_data, assess_and_update_class
from backtesting import Strategy
from backtesting.lib import crossover
from backtesting import Backtest
from pandas import DataFrame, to_datetime


views = Blueprint('views', __name__)

@views.route('/', methods=['GET', 'POST'])
def home():
    # Select all records from the Stocks table

    latest_quarterly_reports = (
    db.session.query(
        Ratiottm.stock_code,
        func.max(Ratiottm.rDate).label('latest_rDate')
    )
    .group_by(Ratiottm.stock_code)
    .subquery()
)
    all_stocks = (
        db.session.query(Stocks)
        .join(latest_quarterly_reports, and_(
            Stocks.stock_code == latest_quarterly_reports.c.stock_code,
            Ratiottm.stock_code == latest_quarterly_reports.c.stock_code,
            Ratiottm.rDate == latest_quarterly_reports.c.latest_rDate
        ))
        .filter(Ratiottm.rClass.in_(['A', 'S','B','C','D']))
        .all()
)

    selected_stocks = (
        db.session.query(Stocks)
        .join(latest_quarterly_reports, and_(
            Stocks.stock_code == latest_quarterly_reports.c.stock_code,
            Ratiottm.stock_code == latest_quarterly_reports.c.stock_code,
            Ratiottm.rDate == latest_quarterly_reports.c.latest_rDate
        ))
        .filter(Ratiottm.rClass.in_(['A', 'S']))
        .all()
)
    return render_template("home.html", user=current_user, company=all_stocks, attention=selected_stocks)


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

      # Get the latest date ratio record for the stock_code
    pastratios = (
        db.session.query(Ratiottm)
        .filter_by(stock_code=company.stock_code)
        .order_by(desc(Ratiottm.rDate))
        .all()
    )
    # Convert the list of objects to a list of dictionaries
    pastratios_data = [
        {
            'stock_code': ratio.stock_code,
            'rDate': ratio.rDate,
            'rEPS': ratio.rEPS,
            'rPE': ratio.rPE,
            'rROE': ratio.rROE,
            'rOM': ratio.rOM,
            'rDY': ratio.rDY,
            'rPR': ratio.rPR,
            'rClass': ratio.rClass,
            'rFCF': ratio.rFCF,
            # Add other fields as needed
        }
        for ratio in pastratios
    ]

    print(f"Past Ratio Stock Code {pastratios[0].stock_code}")

    # Calculate the average of the first 3 records for each ratio column and round to 3 decimal places
    average_eps = round(sum(r.rEPS for r in pastratios[:3]) / 3, 3)
    average_pe = round(sum(r.rPE for r in pastratios[:3]) / 3, 3)
    average_roe = round(sum(r.rROE for r in pastratios[:3]) / 3, 3)
    average_om = round(sum(r.rOM for r in pastratios[:3]) / 3, 3)
    average_dy = round(sum(r.rDY for r in pastratios[:3]) / 3, 3)
    average_pr = round(sum(r.rPR for r in pastratios[:3]) / 3, 3)
    average_class = 'Forecast'  # You can set this as 'Forecast' or any other value you prefer.
    average_fcf = round(sum(r.rFCF for r in pastratios[:3]) / 3, 3)
    

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
        'rFCF': average_fcf
    }

    # Calculate the 'rClass' based on the choices
    dividend_condition = (forecast_data['rDY'] >= 0.02) & (forecast_data['rPR'] >= 0.1) & (forecast_data['rPR'] <= 0.75)
    foundation_condition = (forecast_data['rOM'] >= 0.1) & (forecast_data['rFCF'] >= 0) & (forecast_data['rPE'] <= 10) & (forecast_data['rROE'] >= 0.20) & (forecast_data['rEPS'] >= 0.1)

    if dividend_condition & foundation_condition:
        forecast_data['rClass'] = 'A'
        a_class = True
    elif foundation_condition:
        forecast_data['rClass'] = 'B'
    elif dividend_condition:
        forecast_data['rClass'] = 'C'
    else:
        forecast_data['rClass'] = 'D'

    pastratios_data.insert(0, forecast_data)
    print("Past Ratios:")
    print(pastratios_data)
    pastratios_data = pastratios_data[::-1]
    assess_and_update_class(pastratios_data)

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

        
    return render_template('detail.html', user=current_user, company=company, ratios=ratios, pastratios_data=pastratios_data, price_14=price_14, dividend_records=dividend_records,is_in_watchlist=is_in_watchlist, prices=prices, average_monthly_data = average_monthly_data,weekly_average_data=weekly_average_data, rEPS_data=rEPS_data,rPE_data=rPE_data,rROE_data=rROE_data,rOM_data=rOM_data, rDY_data=rDY_data, rPR_data=rPR_data, rFCF_data=rFCF_data, dividend_data=dividend_data, watchlist_count=watchlist_count)

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

        purchase_price = round(prices[0].Close,3)
        latest_price = round(prices[-1].Close,3)

        # Access the first and last record's Close column
        purchase_value = round(prices[0].Close * unit_quantity, 3)
        latest_value = round(prices[-1].Close * unit_quantity, 3)

        value_diff = round(latest_value - purchase_value, 3)
        value_perc = round(value_diff / purchase_value * 100, 3)

        print("Purchase Date: " + str(purchase_date) + " Latest Date " + str(latest_date))
        print("Purchase Price: " + str(purchase_value) + " Latest Price " + str(latest_value))
        print("Price Difference: " + str(value_diff) + " Price Percentage " + str(value_perc))

        dividends = (
            Dividend.query
            .filter(Dividend.stock_code == stock_code)
            .filter(Dividend.dExDate >= purchase_date, Dividend.dExDate <= latest_date)
            .all()
        )

        # Calculate the dividend amount
        dividend_amount = sum(dividend.dAmount for dividend in dividends) * unit_quantity



        # Calculate the dividend yield
        dividend_yield = dividend_amount / purchase_value

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


    return render_template('backtest.html', user=current_user, stocks=stock_codes, max_date=max_date)


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
            .filter(ranked_quarter_subquery.c.row_num <= 3) # This gets 3 latest quarterly reports of each stock codes for calculating TTM ratios. When at least one new quarterly report (n) is found in Bursa, proceed to calculate TTM ratio with at least 3+n latest records then.
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

@views.route('/delete_portfolio/<int:portfolio_id>', methods=['POST'])
@login_required
def delete_portfolio(portfolio_id):
    # Find and delete the portfolio row with the given ID from the database
    portfolio = Portfolio.query.get(portfolio_id)
    if portfolio:
        db.session.delete(portfolio)
        db.session.commit()
        flash("Row deleted successfully", "success")  # Optionally, you can use Flask flash messages
    else:
        flash("Row not found", "error")
    
    # Redirect back to the page displaying the table
    return redirect(url_for('views.profile'))  # Replace with the correct route name

@views.route('/portfolio', methods=['GET', 'POST'])
@login_required
def profile():
    # Select all records from the Stocks table
       
    # Query the Portfolio records for the current user
        # Query the Portfolio records and join with Stocks to get stock_name
   # Query the Portfolio records for the current user, including the stock_name
    portfolio_results = db.session.query(Portfolio, Stocks.stock_name).join(Stocks).filter(Portfolio.user_id == current_user.id).all()


    
     # Process each stock in the portfolio
    calculation_results = []  # Store the results for each stock
    price_diff_data = {}  # Store the total daily price difference for all stocks
    combined_dividends = []

        # Gather all dividend records within the specified date range

    end_date = date.today() - timedelta(days=1)

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

            # Calculate the daily price difference for the last 30 days for each stock
            price_diff_data_per_stock = []
            for i in range(120):
                date_range_start = latest_date - timedelta(days=i)
                date_range_end = date_range_start + timedelta(days=1)

                # Filter prices for the specific date range
                prices_in_range = [price.Close for price in prices if date_range_start <= price.Date < date_range_end]

                if prices_in_range:
                    price_diff = round(prices_in_range[-1] - prices[0].Close, 3)
                    price_diff_data_per_stock.append({"date": date_range_start, "price_diff": price_diff})

            # Add the daily price differences for the current stock to the total
            for item in price_diff_data_per_stock:
                date_key = item['date'].strftime("%Y-%m-%d")
                if date_key not in price_diff_data:
                    price_diff_data[date_key] = 0
                price_diff_data[date_key] += item['price_diff']


        purchase_price = round(prices[0].Close,3)
        latest_price = round(prices[-1].Close,3)

        price_diff = round(latest_price - purchase_price, 3)


        # Access the first and last record's Close column
        purchase_amount = round(prices[0].Close * unit_quantity, 3)
        latest_amount = round(prices[-1].Close * unit_quantity, 3)

        amount_diff = round(latest_amount - purchase_amount, 3)
        amount_perc = round(amount_diff / purchase_amount * 100, 3)

        dividends = (
            Dividend.query
            .filter(Dividend.stock_code == stock_code)
            .filter(Dividend.dExDate >= purchase_date, Dividend.dExDate <= latest_date)
            .all()
        )
            # Multiply each dividend amount by the unit quantity and store it in combined_dividends
        for dividend in dividends:
            dividend_amount2 = round(dividend.dAmount * unit_quantity, 3)
            combined_dividends.append({"date": dividend.dExDate.strftime("%Y-%m-%d"), "dividend_amount": dividend_amount2})

        # Calculate the dividend amount
        dividend_amount = round(sum(dividend.dAmount for dividend in dividends) * unit_quantity, 3)

        # Calculate the dividend yield
        dividend_yield = round(dividend_amount / purchase_amount,3)

        # Store the results for this stock
        calculation_result = {
            "stock_name": stock_name,
            "stock_code": stock_code,
            "purchase_date": purchase_date,
            "latest_date": latest_date,
            "purchase_price": purchase_price,
            "latest_price": latest_price,
            "price_diff": price_diff,
            "purchase_amount": purchase_amount,
            "latest_amount": latest_amount,
            "amount_diff": amount_diff,
            "amount_perc": amount_perc,
            "dividend_amount": dividend_amount,
            "dividend_yield": dividend_yield
        }
        calculation_results.append(calculation_result)
    
    # Sort combined_dividends by date
    combined_dividends.sort(key=lambda x: x['date'])

    # Calculate the cumulative sum of dividend amounts
    cumulative_dividend_sum = 0
    for dividend in combined_dividends:
        cumulative_dividend_sum += dividend['dividend_amount']
        dividend['cumulative_sum'] = round(cumulative_dividend_sum, 3)

    # Print or return the results, depending on your needs
    # for calculation_result in calculation_results:
    #     print(calculation_result)

    # Print or return the results, depending on your needs
    price_diff_x_y_format = [
        {'x': date_key, 'y': total_price_diff}
        for date_key, total_price_diff in price_diff_data.items()
    ]
    cumulative_dividend_x_y_format = [
    {'x': dividend['date'], 'y': dividend['cumulative_sum']}
    for dividend in combined_dividends
    ]
    # Print or return the results, depending on your needs
    for cumulative_dividend in cumulative_dividend_x_y_format:
        print(f"Date: {cumulative_dividend['x']}, Cumulative Dividend: {cumulative_dividend['y']}")
    # Print the combined dividends
    # for dividend in combined_dividends:
    #     print(f"Date: {dividend['date']}, Dividend Amount: {dividend['dividend_amount']}, Cumulative Sum: {dividend['cumulative_sum']}")
    # for date_key, total_price_diff in price_diff_data.items():
    #     print(f"Date: {date_key}, Total PriceDiff: {total_price_diff}")
    # Print the x and y format for the total daily price difference
    for item in price_diff_x_y_format:
        print(f"Date: {item['x']}, Total PriceDiff: {item['y']}")
    
    return render_template("portfolio.html", user=current_user,  portfolio_and_calculation_results=zip(portfolio_results, calculation_results), price_diff_x_y_format=price_diff_x_y_format, cumulative_dividend_x_y_format=cumulative_dividend_x_y_format)


def SMA(values, n):
    """
    Return simple moving average of `values`, at
    each step taking into account `n` previous values.
    """
    return pd.Series(values).rolling(n).mean()

class SingleSma100(Strategy):
    # Define the moving average lag as a *class variable*
    n = 100
    
    def init(self):
        # Precompute the moving average
        self.sma = self.I(SMA, self.data.Close, self.n)
    
    def next(self):
        # If the close price crosses above the 200-day moving average,
        # close any existing short trades, and buy the asset
        if crossover(self.data.Close, self.sma):
            self.position.close()
            self.buy()

        # Else, if the close price crosses below the 200-day moving average,
        # close any existing long trades, and sell the asset
        elif crossover(self.sma, self.data.Close):
            self.position.close()
            self.sell()
            
class SingleSma50(Strategy):
    # Define the moving average lag as a *class variable*
    n = 50
    
    def init(self):
        # Precompute the moving average
        self.sma = self.I(SMA, self.data.Close, self.n)
    
    def next(self):
        # If the close price crosses above the 200-day moving average,
        # close any existing short trades, and buy the asset
        if crossover(self.data.Close, self.sma):
            self.position.close()
            self.buy()

        # Else, if the close price crosses below the 200-day moving average,
        # close any existing long trades, and sell the asset
        elif crossover(self.sma, self.data.Close):
            self.position.close()
            self.sell()

class SingleSma20(Strategy):
    # Define the moving average lag as a *class variable*
    n = 20
    
    def init(self):
        # Precompute the moving average
        self.sma = self.I(SMA, self.data.Close, self.n)
    
    def next(self):
        # If the close price crosses above the 200-day moving average,
        # close any existing short trades, and buy the asset
        if crossover(self.data.Close, self.sma):
            self.position.close()
            self.buy()

        # Else, if the close price crosses below the 200-day moving average,
        # close any existing long trades, and sell the asset
        elif crossover(self.sma, self.data.Close):
            self.position.close()
            self.sell()

@views.route('/technical_analysis/<stock_code>', methods=['POST'])
@login_required
def technical_analysis(stock_code):
    # Query historical prices for the selected stock code
    start_date = datetime(2021, 11,20)

    # Query historical prices for the selected stock code between start_date and today
    historical_prices = Price.query.filter(
        (Price.stock_code == stock_code) &
        (Price.Date >= start_date)
    ).order_by(Price.Date).all()

    # Convert historical_prices to a pandas DataFrame
    df_columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'stock_code']
    df_data = [(price.Date, price.Open, price.High, price.Low, price.Close, price.Volume, price.stock_code) for price in historical_prices]
    historical_prices_df = DataFrame(data=df_data, columns=df_columns)

    historical_prices_df['Date'] = to_datetime(historical_prices_df['Date'])
    historical_prices_df.set_index('Date', inplace=True)

    selected_days = int(request.form.get('number_of_days'))
    if (selected_days == 20):
        bt = Backtest(historical_prices_df, SingleSma20, cash=10000, commission=0)
    elif (selected_days == 50):
        bt = Backtest(historical_prices_df, SingleSma50, cash=10000, commission=0)
    elif (selected_days == 100):
        bt = Backtest(historical_prices_df, SingleSma100, cash=10000, commission=0)

    stats = bt.run()
    print(stats)

    bt.plot()
   

    # Render the detail.html template with the necessary data
    return redirect(url_for('views.detail', id=stock_code))