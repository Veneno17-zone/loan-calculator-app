import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ---------------------- Depreciation Dataset ----------------------
# Simulated depreciation curves by make/model/year (replace with real data or API)
car_depreciation_data = {
    ("Toyota", "Corolla", 2022): [0.90, 0.82, 0.75, 0.68, 0.62],  # Yearly multipliers
    ("Honda", "Civic", 2022): [0.89, 0.80, 0.73, 0.66, 0.60],
    ("Ford", "F-150", 2022): [0.88, 0.79, 0.70, 0.63, 0.58],
}

# ---------------------- Loan Calculator ----------------------
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

# ---------------------- Car Value Estimator ----------------------
def estimate_car_value_curve(make, model, year, initial_value, months):
    yearly_multipliers = car_depreciation_data.get((make, model, year))
    if not yearly_multipliers:
        yearly_multipliers = [0.88, 0.79, 0.70, 0.63, 0.58]  # Default curve

    monthly_multipliers = []
    for i in range(months):
        year_index = min(i // 12, len(yearly_multipliers) - 1)
        next_index = min(year_index + 1, len(yearly_multipliers) - 1)
        t = (i % 12) / 12
        interp = (1 - t) * yearly_multipliers[year_index] + t * yearly_multipliers[next_index]
        monthly_multipliers.append(interp)

    return [round(initial_value * m, 2) for m in monthly_multipliers]

# ---------------------- Plot Charts ----------------------
def plot_loan_vs_car_value_chart(df, show_car_value=False):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["Month"],
        y=df["Remaining Balance"],
        mode='lines+markers',
        name='Loan Balance',
        line=dict(color='royalblue', width=3),
        hovertemplate='Month %{x}<br>Loan Balance: $%{y:,.2f}<extra></extra>'
    ))
    if show_car_value and "Estimated Car Value" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["Month"],
            y=df["Estimated Car Value"],
            mode='lines+markers',
            name='Car Value',
            line=dict(color='orange', width=3, dash='dash'),
            hovertemplate='Month %{x}<br>Car Value: $%{y:,.2f}<extra></extra>'
        ))
    fig.update_layout(
        title='🚘 Loan vs. Car Value Over Time',
        xaxis_title='Month',
        yaxis_title='Amount ($)',
        hovermode='x unified',
        template='plotly_white'
    )
    return fig

def plot_pie_chart(principal, interest):
    labels = ['Principal', 'Interest']
    values = [round(principal, 2), round(interest, 2)]
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.4,
        hovertemplate='%{label}: $%{value:,.2f}<extra></extra>',
        texttemplate='%{label}<br>$%{value:,.2f}',
        textposition='inside'
    )])
    fig.update_layout(title='💰 Loan Payment Breakdown', template='plotly_white')
    return fig

# ---------------------- Streamlit UI ----------------------
st.set_page_config(page_title="Loan Calculator", layout="wide")
st.title("🚗🏠 Loan Payment Calculator")

loan_type = st.selectbox("Choose loan type", ["Car Loan", "Home Loan"])
price_label = "Home Price ($)" if loan_type == "Home Loan" else "Car Price ($)"
total_price = st.number_input(price_label, min_value=1000, step=1000, value=20000)

# Home Loan specific
down_payment = 0
if loan_type == "Home Loan":
    down_payment = st.number_input("Down Payment ($)", min_value=0, step=1000, value=2000)

principal = total_price - down_payment
st.markdown(f"💵 **Loan Amount to Finance:** ${principal:,.2f}")

annual_rate = st.number_input("Annual Interest Rate (APR %)", min_value=0.1, max_value=25.0, value=5.0, step=0.1)
years = st.number_input("Loan Term (Years)", min_value=1, max_value=10, value=5)
extra_payment = st.number_input("Extra Monthly Payment ($)", min_value=0, step=50, value=0)
fees = st.number_input("Additional Fees ($)", min_value=0, step=50, value=0)
balloon_payment = st.number_input("Balloon Payment ($)", min_value=0, step=1000, value=0) if loan_type == "Car Loan" else 0
start_date = st.date_input("Loan Start Date", value=datetime.today())

# Car model input if applicable
if loan_type == "Car Loan":
    make = st.selectbox("Car Make", ["Toyota", "Honda", "Ford"])
    model = st.selectbox("Car Model", ["Corolla", "Civic", "F-150"])
    year = st.selectbox("Car Year", [2022, 2023, 2024])

if st.button("Calculate Loan"):
    df, total_interest, total_paid, months = calculate_amortization_schedule(
        principal, annual_rate, years, extra_payment,
        start_date.strftime("%Y-%m-%d"), fees, balloon_payment
    )

    st.subheader(f"📆 Loan paid off in {months} months")
    st.write(f"💸 Total interest paid: ${total_interest:,.2f}")

    if loan_type == "Car Loan":
        car_values = estimate_car_value_curve(make, model, year, total_price, months)
        df["Estimated Car Value"] = pd.Series(car_values).round(2)

        df["Remaining Balance"] = df["Remaining Balance"].round(2)
        df["Negative Equity"] = df["Remaining Balance"] > df["Estimated Car Value"]

        if df["Negative Equity"].any():
            first_neg = df[df["Negative Equity"]].iloc[0]
            st.warning(f"⚠️ Negative equity begins in Month {first_neg['Month']} ({first_neg['Date']})")
        else:
            st.success("✅ No negative equity during loan term.")

        st.plotly_chart(plot_loan_vs_car_value_chart(df, show_car_value=True), use_container_width=True)
    else:
        df["Remaining Balance"] = df["Remaining Balance"].round(2)
        st.plotly_chart(plot_loan_vs_car_value_chart(df, show_car_value=False), use_container_width=True)

    st.plotly_chart(plot_pie_chart(principal, total_interest), use_container_width=True)

    # Format and style table
    format_dict = {col: "{:,.2f}" for col in df.select_dtypes(include='number').columns}
    styled_df = df.style.format(format_dict)
    if "Negative Equity" in df.columns:
        styled_df = styled_df.apply(
            lambda x: ["background-color: #ffcdd2" if v else "" for v in x],
            subset=["Negative Equity"]
        )
    st.dataframe(styled_df, use_container_width=True)

    # Download CSV
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download CSV", data=csv, file_name="loan_schedule.csv", mime='text/csv')
