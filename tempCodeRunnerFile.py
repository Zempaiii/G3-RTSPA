# Bollinger Bands
        close_prices = [entry["c"] for entry in results]
        window = 20
        num_std_dev = 2

        rolling_mean = pd.Series(close_prices).rolling(window).mean()
        rolling_std = pd.Series(close_prices).rolling(window).std()

        upper_band = rolling_mean + (rolling_std * num_std_dev)
        lower_band = rolling_mean - (rolling_std * num_std_dev)

        # Initialize the figure
        fig = go.Figure()

        # Add Bollinger Bands to the plot
        fig.add_trace(go.Scatter(
            x=dates,
            y=upper_band,
            name='Upper Band',
            line=dict(color='rgba(255, 0, 0, 0.5)')
        ))

        fig.add_trace(go.Scatter(
            x=dates,
            y=rolling_mean,
            name='Middle Band',
            line=dict(color='rgba(0, 0, 255, 0.5)')
        ))

        fig.add_trace(go.Scatter(
            x=dates,
            y=lower_band,
            name='Lower Band',
            line=dict(color='rgba(0, 255, 0, 0.5)')
        ))
