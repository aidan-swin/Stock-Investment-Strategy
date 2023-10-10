from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for, Response
from flask_login import  login_required,  current_user
from .models import CompanyInfo, User, Stocks, Ratio
from . import db
import json
import pickle
import numpy as np
import pandas as pd
import csv
import shap
import datetime
from sqlalchemy.sql import func, desc
from sklearn.preprocessing import StandardScaler
from sklearn.inspection import permutation_importance
from .custom_shap import TreeExplainer

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
    company = CompanyInfo.query.all()
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
            for item in company:
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
    return render_template("watchlist.html", user=current_user, company=company)


@views.route('/detail/<string:id>')
@login_required
def detail(id):
    company = Stocks.query.get_or_404(id)
    
    # Get the latest date ratio record for the stock_code
    ratios = (
        db.session.query(Ratio)
        .filter_by(stock_code=company.stock_code)
        .order_by(desc(Ratio.rDate))
        .first()
    )
    
    return render_template('detail.html', user=current_user, company=company, ratios=ratios)

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
def add_companyInfo():
    if request.method =='POST':
        companyname_f = request.form.get('companyname')
        equity_ratio_f = request.form.get('equity_ratio')
        liabilities_coverage_f = request.form.get('liabilities_coverage')
        operating_profit_margin_to_financial_expense_f = request.form.get('operating_profit_margin_to_financial_expense')
        working_capital_to_fixed_assets_f = request.form.get('working_capital_to_fixed_assets')
        current_liabilities_by_365_by_cost_of_products_sold_f = request.form.get('current_liabilities_by_365_by_cost_of_products_sold')
        operating_expenses_to_total_liabilities_f = request.form.get('operating_expenses_to_total_liabilities')
        current_assets_without_inventories_to_long_term_liabilities_f = request.form.get('current_assets_without_inventories_to_long_term_liabilities')
        liability_to_operating_profit_ratio_per_day_f = request.form.get('liability_to_operating_profit_ratio_per_day')
        net_profit_to_inventory_f = request.form.get('net_profit_to_inventory')
        assets_without_inventories_and_short_term_liabilities_to_sales_without_gross_profit_and_depreciation_f = request.form.get('assets_without_inventories_and_short_term_liabilities_to_sales_without_gross_profit_and_depreciation')
        forecast_period_f = request.form.get('forecast_period')

        if len(companyname_f) < 1:
            flash('Required Fields not complete.', category='error')
        else:
            with open('D:/VisualStudioCode/BRS_Official/BRS/random_forest_model.pkl', 'rb') as f:
                rf = pickle.load(f)
          # Input values for prediction
            input_values = np.array([equity_ratio_f, liabilities_coverage_f, operating_profit_margin_to_financial_expense_f,
                                    working_capital_to_fixed_assets_f, current_liabilities_by_365_by_cost_of_products_sold_f,
                                    operating_expenses_to_total_liabilities_f,
                                    current_assets_without_inventories_to_long_term_liabilities_f,
                                    liability_to_operating_profit_ratio_per_day_f, net_profit_to_inventory_f,
                                    assets_without_inventories_and_short_term_liabilities_to_sales_without_gross_profit_and_depreciation_f,
                                    forecast_period_f])

            # Load the saved scaler object
            with open('D:/VisualStudioCode/BRS_Official/BRS/scaler.pkl', 'rb') as f:
                scaler = pickle.load(f)

            # Scale the input values
            input_values_scaled = scaler.transform([input_values])

            # Use the trained Random Forest model for prediction
            prediction = rf.predict(input_values_scaled)

            # Print the prediction
            print(f'Prediction: {prediction}')
            risk=rf.predict_proba(input_values_scaled)[:, 1]
            risk=np.round(risk,2)
            print(risk) 

            # Get the risk probability
            risk = rf.predict_proba(input_values_scaled)[:, 1]
            risk = np.round(risk, 2)

            # Create a TreeExplainer object with the trained model
            explainer = shap.TreeExplainer(rf)

            # Get the SHAP values for the specific record
            shap_values = explainer.shap_values(input_values_scaled, check_additivity=False)

            # Sum the absolute SHAP values across features for the specific record
            feature_importances = np.abs(shap_values).mean(axis=0)

            # Normalize the feature importances so that they sum up to 1
            normalized_importances = feature_importances / np.sum(feature_importances)

            # Print the normalized feature importances
            for importance in normalized_importances:
                print(f"Importance: {importance}")

           # Store the normalized importances in a 1D array to be stored in database
            importance_array = normalized_importances.flatten()

            # Print the importance array
            print(importance_array[0])

            # Calculate the sum of all the elements in the normalized_importances array
            sum_importances = np.sum(normalized_importances)
            print(f"Sum of importances: {sum_importances}")

            new_companyinfo= CompanyInfo(companyname=companyname_f,
                                        equity_ratio=equity_ratio_f,
                                         liabilities_coverage=liabilities_coverage_f,
                                         operating_profit_margin_to_financial_expense=operating_profit_margin_to_financial_expense_f, 
                                         working_capital_to_fixed_assets=working_capital_to_fixed_assets_f,
                                         current_liabilities_by_365_by_cost_of_products_sold=current_liabilities_by_365_by_cost_of_products_sold_f,
                                         operating_expenses_to_total_liabilities=operating_expenses_to_total_liabilities_f,
                                         current_assets_without_inventories_to_liabilities=current_assets_without_inventories_to_long_term_liabilities_f,
                                         liability_to_operating_profit_ratio_per_day=liability_to_operating_profit_ratio_per_day_f,
                                         net_profit_to_inventory=net_profit_to_inventory_f,
                                         assets_without_inventories_and_short_term_liabilities_to_sales_without_gross_profit_and_depreciation=assets_without_inventories_and_short_term_liabilities_to_sales_without_gross_profit_and_depreciation_f,
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
                                         forecast_period = forecast_period_f,
                                        Bankrupt=prediction, 
                                           user_id = current_user.id, 
                                           Risk=risk)     
            db.session.add(new_companyinfo)
            db.session.commit()
            flash('New company information added!', category='success')
            return render_template("detail.html", user=current_user, company=new_companyinfo)

    return render_template("backtest.html", user=current_user)

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


