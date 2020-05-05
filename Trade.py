from app.technical_indicators import Technical_Calculations
from app.indicator_analysis import Indications, Price_Action
from app.exchange_api import *
from app.exchange_preprocessing import *
from app.model import ML
import datetime as dt
import streamlit as st
import pandas as pd
import numpy as np
from _plotly_future_ import v4_subplots
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from pandas.plotting import register_matplotlib_converters
from plotly.offline import download_plotlyjs, init_notebook_mode, plot, iplot
import cufflinks as cf

register_matplotlib_converters()
init_notebook_mode(connected = True)
cf.go_offline()


def load_data(stock, market, interval, exchange, label):

    if exchange == 'Yahoo Finance':
        stock_ticker = stock_to_ticker(stock) 
        period, stock_interval = yahoo_interval(interval) 
    else:
        cypto_ticker = crypto_to_ticker(stock)
        market_ticker = crypto_markets_to_ticker(market)
        interval = crypto_interval(exchange, interval)

    if exchange == 'Binance':
        df = binance_market_data(cypto_ticker, market_ticker, interval)
    elif exchange == 'Bitfinex':
        df = bitfinex_market_data(cypto_ticker, market_ticker, interval)
    elif exchange == 'Bittrex':
        df = bittrex_market_data(cypto_ticker, market_ticker, interval)
    else:
        df = yahoo_market_data(stock_ticker, period, stock_interval)

    df = df.iloc[-650:]
    requested_date = df.index[-1]
    current_price = df.iloc[-1,-1]

    if label == 'Stock':
        current_price = current_price.round(2)
    else:
        current_price = current_price.round(8)

    return df, str(requested_date), str(current_price)

def analyse(df):

    Technical_Calculations(df, df['Adj Close'], df['High'], df['Low'])
    df.dropna(inplace = True)
    analysis = analysis = df.loc[:, 'MACD':'SR_D']

    return analysis, df

def indications(df):

    Indications(df, df['Adj Close'], df['Open'])
    Price_Action(df)
    df.dropna(inplace = True)

    return df

def graph(Stock, ticker, data, model_prediction, indication):

    prediction_length = model_prediction.shape[0]
    df = data.iloc[-prediction_length:]
    df['Model_Predictions'] = model_prediction
    df = df[['Adj Close', 'General_Action', 'Distinct_Action', 'Model_Predictions']]
    df = df.iloc[-100:]

    if indication == 'General':

        df['Action'] = df['General_Action']

        action = pd.get_dummies(df['Action'], prefix='Action', prefix_sep='_', dummy_na = False, dtype='int32')
        df = pd.concat([df, action], axis = 1)
        
    elif indication == 'Distinct':

        df['Action'] = df['Distinct_Action']

        action = pd.get_dummies(df['Action'], prefix='Action', prefix_sep='_', dummy_na = False, dtype='int32')
        df = pd.concat([df, action], axis = 1)

    elif indication == 'Model Prediction':

        df.loc[((df['Model_Predictions'] == 'Buy')), 'Action_Buy'] = 1
        df.loc[((df['Model_Predictions'] == 'Sell')), 'Action_Sell'] = 1
        df['Action_Buy'].fillna(0, inplace = True)
        df['Action_Sell'].fillna(0, inplace = True)

    fig = make_subplots(specs = [[{"secondary_y": True}]])
    
    fig.add_trace(go.Scatter(x = df.index, y = df['Adj Close'], name = "Close Price"), secondary_y = True)
    fig.add_trace(go.Bar(x = df.index, y = df['Action_Sell'], name = "Sell"), secondary_y = False)
    fig.add_trace(go.Bar(x = df.index, y = df['Action_Buy'], name = "Buy"), secondary_y = False)

    fig.update_layout(autosize = False, width = 950, height = 600)
    fig.layout.update(title_text = f"{Stock} to {ticker}")
    fig.update_xaxes(title_text = "Date")
    fig.update_yaxes(title_text = "Close Price", secondary_y = True)
    fig.update_yaxes(title_text = "Price Action", secondary_y = False)

    return fig, df

def main():
    
    st.sidebar.subheader('Exchange:')
    exchange = st.sidebar.selectbox('', ('Yahoo Finance', 'Binance', 'Bittrex'))

    markets = stock_crypto_markets(exchange)

    if exchange == 'Yahoo Finance':
        st.sidebar.subheader('Stock:')
        stock = st.sidebar.selectbox('', markets)

        if stock == 'Airbus' or stock == 'BMW' or stock == 'Volkswagen':
            market = 'Euros'
        elif stock == 'Samsung':
            market = 'Korean Won'
        else:
            market = 'US Dollar'

        interval = st.sidebar.selectbox('', ('1 Hour', '1 Day', '1 Week'))        
        label = 'Stock'

    else:

        st.sidebar.subheader('Market:')
        market = st.sidebar.selectbox('', markets)

        coins = exchange_to_coins_loading (exchange, market)
        
        st.sidebar.subheader('Crypto:')
        stock = st.sidebar.selectbox('', coins)

        st.sidebar.subheader('Interval:')
        
        if exchange == 'Bitfinex':
            interval = st.sidebar.selectbox('', ('1 Minute', '5 Minute', '15 Minute', '30 Minute', '1 Hour'))
        else:
            interval = st.sidebar.selectbox('', ('1 Minute', '5 Minute', '15 Minute', '30 Minute', '1 Hour', '1 Day'))

        label = 'Cryptocurrency'

    st.sidebar.subheader('Indication:')
    indication = st.sidebar.selectbox('', ('Model Prediction', 'Distinct', 'General'))

    st.title(f'Simple Technical Analysis for {label} Trading.')
    st.subheader(f'{label} Data Sourced from {exchange} in {interval} Interval.')
    st.info(f'Predicting...')

    data, requested_date, current_price = load_data(stock, market, interval, exchange, label)

    st.sidebar.info('Advanced Options:')
    if st.sidebar.checkbox('The Sourced Data'):
        st.success ('Sourcing...')
        st.write(data.tail(10))
        st.text ('Done!')
    
    analysis, data = analyse(data) 

    if st.sidebar.checkbox('Technical Analysis Performed'):
            st.success ('Analyzing...')
            st.write(analysis.tail(10))
            st.text("Done!!!")

    data = indications(data)

    if exchange != 'Yahoo Finance':
        if market == 'Bitcoin':
            currency = 'BTC '
        elif market == 'Ethereum':
            currency = 'ETH '
        elif market == 'Tether':
            currency = 'USDT '
        else:
            currency = 'USD '
    elif stock == 'Airbus' or stock == 'BMW' or stock == 'Volkswagen':
        currency = 'EUR '
    elif stock == 'Samsung':
        currency = 'KRW '
    else:
        currency = 'USD '

    st.cache()
    requested_prediction_now, requested_prediction_future, model_prediction_now, score_now, score_future = ML(data)

    if requested_prediction_now == 'Hold':
        present_statement = 'off from preforming any action with'
    else:
        present_statement = ''

    if requested_prediction_future == 'Hold':
        future_statement = 'off from preforming any action with'
    else:
        future_statement = ''

    st.markdown(f'**Date Predicted:** {requested_date}')
    st.markdown(f'**Current Price:** {currency} {current_price}')
    st.markdown(f'**Current Trading Prediction:** You should **{requested_prediction_now}** {present_statement} this {label.lower()}.')
    st.markdown(f'**Future Trading Prediction:** You should consider **{requested_prediction_future}ing** {future_statement} this {label.lower()} in the next {int(interval.split()[0]) * 10} {str(interval.split()[1]).lower()}s.')
    st.markdown(f'**Current Trading Prediction Confidence:** {score_now}%')
    st.markdown(f'**Future Trading Prediction Confidence:** {score_future}%')

    st.cache()
    fig, df = graph(stock, market, data, model_prediction_now, indication)

    st.success(f'Backtesting {label} Data...')
    st.plotly_chart(fig)
    
if __name__ == '__main__':
    main()