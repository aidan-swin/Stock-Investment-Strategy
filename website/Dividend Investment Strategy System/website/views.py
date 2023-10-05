from flask import Blueprint, render_template, request, flash, jsonify
from flask_login import  login_required,  current_user
from .models import Note, CompanyInfo
from . import db
import json
import pickle
import sklearn
import requests
from bs4 import BeautifulSoup
import datetime as dt

views = Blueprint('views', __name__)

import pandas_datareader.data as pdr
import yfinance as yf

def get_stock_data(symbol, start_date):
    try:
        # Convert the start_date string to a datetime object
        startdate = dt.datetime.strptime(start_date, '%Y-%m-%d')
        
        # Create a Ticker object for the specified symbol
        ticker = yf.Ticker(symbol)

        # Get historical data (adjust parameters as needed)
        historical_data = ticker.history(period="1d", start=startdate)

        if historical_data.empty:
            print(f"No data available for {symbol} on {startdate}.")
            return None

        # Extract the latest data (usually the last row in the DataFrame)
        latest_data = historical_data.iloc[-1]

        stock = {
            'open': latest_data['Open'],
            'close': latest_data['Close'],
            'dividends': latest_data['Dividends'],
        }

        return stock
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None

@views.route('/', methods=['GET', 'POST'])
@login_required
def home():
    if request.method == 'POST':
        company_symbol = request.form.get('Companysymbol')
        start_date = request.form.get('StartDate')

        if not company_symbol:
            flash('Please enter a company symbol', category='error')
        else:
            stock_data = get_stock_data(company_symbol, start_date)
            if stock_data is None:
                flash('Company symbol not found or data retrieval error!', category='error')
            else:
                new_company_info = CompanyInfo(
                    companyname=company_symbol,
                    price=stock_data['open'],
                    value_diff=stock_data['close'],
                    perc_diff=stock_data['dividends'],
                    user_id=current_user.id
                )
                db.session.add(new_company_info)
                db.session.commit()

                flash('Company information added!', category='success')

    return render_template("home.html", user=current_user)





@views.route('/delete-note', methods=['POST'])
def delete_note():
    note=json.loads(request.data)
    noteId = note['noteId']
    note = Note.query.get(noteId)
    if note:
        if note.user_id == current_user.id:
            db.session.delete(note)
            db.session.commit()
    return jsonify({})

@views.route('/companyinfo', methods=['GET', 'POST'])
@login_required
def companyinfo():
    user_company_info = current_user.company_info.all()
    return render_template("companyinfo.html", user=current_user, user_company_info=user_company_info)


