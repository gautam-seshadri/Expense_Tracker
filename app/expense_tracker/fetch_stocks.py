import yfinance as yf
import matplotlib.pyplot as plt
from matplotlib.widgets import RadioButtons

# Define the stock ticker
ticker = "NIFTYBEES.NS"
stock = yf.Ticker(ticker)

# Define periods
periods = {
    "1 Year": "1y",
    "2 Years": "2y",
    "3 Years": "3y",
    "5 Years": "5y",
    "10 Years": "10y",
    "Max (Since Inception)": "max"
}

# Fetch all data upfront
data = {label: stock.history(period=period) for label, period in periods.items()}

# Create figure and axis
fig, ax = plt.subplots(figsize=(10, 5))
plt.subplots_adjust(left=0.25)  # Adjust space for radio buttons on the left

# Initial plot (Default: 1 Year)
current_period = "1 Year"
line, = ax.plot(data[current_period].index, data[current_period]['Close'], label='Closing Price', color='blue')

# Set initial labels
ax.set_title(f'{ticker} Stock Price Trend ({current_period})')
ax.set_xlabel('Date')
ax.set_ylabel('Closing Price')
ax.legend()

# Create radio buttons
ax_radio = plt.axes([0.05, 0.3, 0.15, 0.4])  # Position of the radio buttons
radio = RadioButtons(ax_radio, list(periods.keys()))

# Function to update plot when a radio button is selected
def update_plot(label):
    new_data = data[label]
    line.set_xdata(new_data.index)
    line.set_ydata(new_data['Close'])
    ax.set_xlim(new_data.index.min(), new_data.index.max())  # Adjust x-axis limits
    ax.set_ylim(new_data['Close'].min() * 0.95, new_data['Close'].max() * 1.05)  # Adjust y-axis
    ax.set_title(f'{ticker} Stock Price Trend ({label})')
    plt.draw()

# Link radio buttons to the update function
radio.on_clicked(update_plot)

# Show interactive plot
plt.show()
