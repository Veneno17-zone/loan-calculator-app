import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

@st.cache_data
def get_car_makes():
    url = "https://www.carqueryapi.com/api/0.3/?cmd=getMakes"
    response = requests.get(url)
    return sorted([make['make_display'] for make in response.json()['Makes']])

@st.cache_data
def get_models(make, year):
    url = f"https://www.carqueryapi.com/api/0.3/?cmd=getModels&make={make}&year={year}"
    response = requests.get(url)
    models = response.json().get("Models", [])
    return sorted(list(set([m['model_name'] for m in models])))

@st.cache_data
def get_trims(make, model, year):
    url = f"https://www.carqueryapi.com/api/0.3/?cmd=getTrims&make={make}&model={model}&year={year}"
    response = requests.get(url)
    trims = response.json().get("Trims", [])
    return sorted(list(set([t['model_trim'] if t['model_trim'] else 'Standard' for t in trims])))

def calculate_amortization_schedule(principal, annual_rate, years, extra_payment=0.0, start_date="2025-07-01", fees=0.0, balloon_payment=0.0):
    monthly_rate = annual_rate / 12 / 100
    months = years * 12
    principal += fees
    monthly_payment = (principal - balloon_payment) * (monthly_rate * (1 + monthly_rate) ** months) / ((1 + monthly_rate) ** months - 1) if monthly_rate else (principal - balloon_payment) / months
    monthly_payment += extra_payment

    balance = principal
    schedule = []
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    total_interest = 0.0

    for month in range(1, months + 1):
        interest = balance * monthly_rate
        principal_paid = min(monthly_payment - interest, balance)
        balance -= principal_paid
        total_interest += interest
        payment_date = start_date + timedelta(days=30 * (month - 1))

        schedule.append([
            month,
            payment_date.strftime("%Y-%m-%d"),
            round(monthly_payment, 2),
            round(principal_paid, 2),
            round(interest, 2),
            round(balance, 2)
        ])

        if balance <= 0:
            break

    if balloon_payment > 0 and balance > 0:
        balance -= balloon_payment
        final_payment_date = start_date + timedelta(days=30 * month)
        schedule.append([
            month + 1,
            final_payment_date.strftime("%Y-%m-%d"),
            round(balloon_payment, 2),
            round(balloon_payment, 2),
            0.0,
            round(balance, 2)
        ])
        month += 1

    df = pd.DataFrame(schedule, columns=["Month", "Date", "Payment", "Principal Paid", "Interest Paid", "Remaining Balance"])
    total_paid = df["Payment"].sum()
    return df, total_interest, total_paid, month

def estimate_car_value_curve(msrp, months):
    depreciation_curve = [1.0, 0.85, 0.75, 0.65, 0.55]
    values = []
    for i in range(months):
        y = i // 12
        next_y = min(y + 1, len(depreciation_curve) - 1)
        t = (i % 12) / 12
        ratio = (1 - t) * depreciation_curve[y] + t * depreciation_curve[next_y]
        values.append(round(msrp * ratio, 2))
    return values

def plot_loan_vs_car_value_chart(df):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['Month'], y=df['Remaining Balance'], mode='lines', name='Loan Balance'))
    if "Estimated Car Value" in df.columns:
        fig.add_trace(go.Scatter(x=df['Month'], y=df['Estimated Car Value'], mode='lines', name='Car Value'))
    fig.update_layout(title='🚘 Loan vs. Car Value Over Time', xaxis_title='Month', yaxis_title='Amount ($)', template='plotly_white')
    return fig

def plot_pie_chart(principal, interest):
    labels = ['Principal', 'Interest']
    values = [round(principal, 2), round(interest, 2)]
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.4)])
    fig.update_layout(title='💰 Loan Payment Breakdown')
    return fig

st.set_page_config(page_title="Loan App", layout="wide")
st.title("🚗🏠 Smart Loan & Car Value Calculator")

loan_type = st.selectbox("Loan Type", ["Car Loan", "Home Loan"])
total_price = st.number_input("Car/Home Price ($)", min_value=1000, step=1000, value=20000)
down_payment = st.number_input("Down Payment ($)", min_value=0, step=1000, value=2000)
principal = total_price - down_payment
st.markdown(f"**Loan Amount:** ${principal:,.2f}")

if loan_type == "Car Loan":
    year = st.selectbox("Year", list(range(datetime.now().year, datetime.now().year - 10, -1)))
    make = st.selectbox("Make", get_car_makes())
    if make:
        models = get_models(make, year)
        model = st.selectbox("Model", models)
        if model:
            trims = get_trims(make, model, year)
            trim = st.selectbox("Trim", trims)

annual_rate = st.number_input("APR (%)", min_value=0.1, max_value=25.0, value=5.0)
years = st.number_input("Loan Term (Years)", min_value=1, max_value=10, value=5)
extra_payment = st.number_input("Extra Monthly Payment ($)", min_value=0, value=0)
fees = st.number_input("Loan Fees ($)", min_value=0, value=0)
balloon = st.number_input("Balloon Payment ($)", min_value=0, value=0) if loan_type == "Car Loan" else 0
start_date = st.date_input("Start Date", value=datetime.today())

if st.button("Calculate Loan"):
    df, interest, total_paid, months = calculate_amortization_schedule(principal, annual_rate, years, extra_payment, start_date.strftime("%Y-%m-%d"), fees, balloon)

    if loan_type == "Car Loan":
        values = estimate_car_value_curve(total_price, months)
        df['Estimated Car Value'] = values
        df['Negative Equity'] = df['Remaining Balance'] > df['Estimated Car Value']
        if df['Negative Equity'].any():
            st.warning("⚠️ Negative equity starts in month " + str(int(df[df['Negative Equity']].iloc[0]['Month'])))
        else:
            st.success("✅ No negative equity during loan term")

    st.subheader(f"Loan paid off in {months} months")
    st.plotly_chart(plot_loan_vs_car_value_chart(df), use_container_width=True)
    st.plotly_chart(plot_pie_chart(principal, interest), use_container_width=True)

    styled = df.style.format({col: "{:.2f}" for col in df.select_dtypes("number").columns})
    st.dataframe(styled, use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download CSV", csv, "loan_schedule.csv", "text/csv")
