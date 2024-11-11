import streamlit as st
import pandas as pd
import yfinance as yf
import ta
import plotly.graph_objs as go

# Set page configuration and title
st.set_page_config(page_title="Advanced Trading Strategy Analyzer")
st.title("Advanced Trading Strategy Analyzer")

# Create a form for input parameters
with st.form(key='input_form'):
    st.header("Input Parameters")
    ticker_input = st.text_input("Ticker Symbol (without .SR for Saudi stocks):", value='1303')
    period = st.selectbox(
        "Period:",
        options=['1y', '2y', '5y', 'max'],
        index=0,
        format_func=lambda x: {'1y': '1 Year', '2y': '2 Years', '5y': '5 Years', 'max': 'All'}.get(x, x)
    )
    sma_short = st.number_input("Short SMA Period:", value=7, min_value=1)
    sma_long = st.number_input("Long SMA Period:", value=10, min_value=1)
    rsi_threshold = st.number_input("RSI Threshold:", value=40, min_value=0, max_value=100)
    adl_short = st.number_input("Short ADL SMA Period:", value=19, min_value=1)
    adl_long = st.number_input("Long ADL SMA Period:", value=25, min_value=1)
    submit_button = st.form_submit_button(label='Analyze')

# Perform analysis when the form is submitted
if submit_button:
    # Check if the ticker is numeric (Saudi stock symbol)
    if ticker_input.isdigit():
        ticker = f"{ticker_input}.SR"
    else:
        ticker = ticker_input

    # Download the data for the ticker
    try:
        df = yf.download(ticker, period=period)
        df.index = pd.to_datetime(df.index)

        if df.empty:
            st.error("No data found for the given ticker and period.")
        else:
            # Calculate indicators
            df['SMA_Short'] = df['Close'].rolling(window=sma_short).mean()
            df['SMA_Long'] = df['Close'].rolling(window=sma_long).mean()
            df['RSI'] = ta.momentum.RSIIndicator(df['Close'], window=14).rsi()
            df['MACD'] = ta.trend.MACD(df['Close']).macd()
            df['MACD_Signal'] = ta.trend.MACD(df['Close']).macd_signal()
            df['ADL'] = ta.volume.AccDistIndexIndicator(
                df['High'], df['Low'], df['Close'], df['Volume']
            ).acc_dist_index()
            df['ADL_Short_SMA'] = df['ADL'].rolling(window=adl_short).mean()
            df['ADL_Long_SMA'] = df['ADL'].rolling(window=adl_long).mean()

            # Signal generation
            df['Signal'] = df.apply(
                lambda row: -1 if row['Close'] >= row['SMA_Short'] and row['SMA_Short'] > row['SMA_Long'] and row['ADL_Short_SMA'] > row['ADL_Long_SMA'] and row['RSI'] >= rsi_threshold and row['MACD'] > row['MACD_Signal'] else (
                    1 if row['Close'] < row['SMA_Short'] and row['SMA_Short'] < row['SMA_Long'] else 0
                ), axis=1
            )

            # Simulate trading
            initial_investment = 100000
            portfolio = initial_investment
            trades = []
            buy_price = None
            trade_start = None
            number_of_trades = 0

            for index, row in df.iterrows():
                if row['Signal'] == 1 and buy_price is None:
                    buy_price = row['Close']
                    trade_start = index
                    number_of_trades += 1
                elif row['Signal'] == -1 and buy_price is not None:
                    sell_price = row['Close']
                    profit = (sell_price - buy_price) * (portfolio / buy_price)
                    portfolio += profit
                    days_held = (index - trade_start).days

                    trades.append({
                        'Sell Date': index.date().strftime('%Y-%m-%d'),
                        'Buy Price': f"{buy_price:.2f} SAR",
                        'Sell Price': f"{sell_price:.2f} SAR",
                        'Days Held': days_held,
                        'Profit': f"{profit:,.2f} SAR",
                        'Profit Percentage': f"{(profit / (portfolio - profit)) * 100:.2f}%"
                    })

                    buy_price = None

            final_value = portfolio
            total_return = final_value - initial_investment
            percentage_return = (total_return / initial_investment) * 100

            # Create the plot with enhanced visuals
            fig = go.Figure()

            # Add the Closing Price and SMA lines
            fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name='Close Price', line=dict(color='blue')))
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA_Short'], mode='lines', name=f'SMA Short ({sma_short})', line=dict(color='orange', dash='dash')))
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA_Long'], mode='lines', name=f'SMA Long ({sma_long})', line=dict(color='green', dash='dot')))

            # Highlight Buy and Sell signals
            buy_signals = df[df['Signal'] == 1]
            sell_signals = df[df['Signal'] == -1]

            fig.add_trace(go.Scatter(x=buy_signals.index, y=buy_signals['Close'], mode='markers', name='Buy Signal', 
                                     marker=dict(color='green', size=12, symbol='triangle-up')))
            fig.add_trace(go.Scatter(x=sell_signals.index, y=sell_signals['Close'], mode='markers', name='Sell Signal', 
                                     marker=dict(color='red', size=12, symbol='triangle-down')))

            fig.update_layout(title=f'Trading Strategy for {ticker}', xaxis_title='Date', yaxis_title='Price', template='plotly_white')

            # Display the plot
            st.plotly_chart(fig)

            # Prepare the summary text
            summary_text = (
                f"Ticker: {ticker}\n"
                f"Initial Investment: {initial_investment:,.2f} SAR\n"
                f"Final Portfolio Value: {final_value:,.2f} SAR\n"
                f"Total Return: {total_return:,.2f} SAR\n"
                f"Percentage Return: {percentage_return:.2f}%\n"
                f"Number of Trades: {number_of_trades}\n"
                f"Average Days Held per Trade: {sum([t['Days Held'] for t in trades]) / number_of_trades if number_of_trades > 0 else 0:.2f} days"
            )

            # Display the summary
            st.header("Best Strategy Summary")
            st.text(summary_text)

            # Create the trades table
            trades_df = pd.DataFrame(trades)

            # Display the trades table
            st.header("Best Trades Details")
            if not trades_df.empty:
                st.table(trades_df)
            else:
                st.write("No trades were made during this period.")

    except Exception as e:
        st.error(f"An error occurred: {e}")
