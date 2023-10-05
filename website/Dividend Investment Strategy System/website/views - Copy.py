from flask import Blueprint, render_template, request, flash, jsonify
from flask_login import  login_required,  current_user
from .models import Note, CompanyInfo
from . import db
import json
import pickle
import sklearn
import requests
from bs4 import BeautifulSoup
import pandas_datareader as pdr

views = Blueprint('views', __name__)



def scrape_stock_data(symbol):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.69'
    }

    url = f'https://uk.finance.yahoo.com/quote/{symbol}'

    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, 'html.parser')

    checktest = soup.find('div', {'class': 'Mt(30px)'})
    data_type = type(checktest)
    print(data_type)
    if checktest is None:
        stock = {
        'price': soup.find('div', {'class': 'D(ib) Mend(20px)'}).find_all('fin-streamer')[0].text,
        'value_diff': soup.find('div', {'class': 'D(ib) Mend(20px)'}).find_all('fin-streamer')[1].text,
        'perc_diff': soup.find('div', {'class': 'D(ib) Mend(20px)'}).find_all('fin-streamer')[2].text
        }
        return stock
    else:
        return
        



@views.route('/', methods=['GET', 'POST'])
@login_required
def home():
    if request.method == 'POST':
        company_symbol = request.form.get('Companysymbol')

        if not company_symbol:
            flash('Please enter a company symbol', category='error')
        else:
            stock_data = scrape_stock_data(company_symbol)
            if stock_data is None:
                flash('Company symbol not found!', category='error')
            else:
                new_company_info = CompanyInfo(
                    companyname=company_symbol,
                    price=stock_data['price'],
                    value_diff=stock_data['value_diff'],
                    perc_diff=stock_data['perc_diff'],
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


