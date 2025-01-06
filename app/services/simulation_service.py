from app.models import Strategy


class SimulationService:
    @staticmethod
    def simulate_strategy(id, data, user_id):
        strategy = Strategy.query.filter_by(id=id).first()

        if not strategy:
            return {"message": "Strategy not found"}, 404

        if strategy.user_id != user_id:
            return {"message": "You can only simulate your own strategies"}, 403

        # Логіка симуляції
        total_trades = 0
        profit_loss = 0.0
        win_trades = 0
        max_drawdown = 0.0
        initial_balance = 10000.0
        balance = initial_balance
        highest_balance = initial_balance

        for day in data:
            try:
                date = day['date']
                close_price = day['close']
                volume = day.get('volume', 1)  # За замовчуванням об'єм = 1
            except KeyError:
                continue

            buy_signal = close_price > strategy.buy_conditions['threshold']
            sell_signal = close_price < strategy.sell_conditions['threshold']

            # Логіка покупки
            if buy_signal:
                total_trades += 1
                balance -= close_price * volume

            # Логіка продажу
            if sell_signal:
                total_trades += 1
                balance += close_price * volume
                win_trades += 1

            # Розрахунок максимальної просадки
            if balance > highest_balance:
                highest_balance = balance
            drawdown = (highest_balance - balance) / highest_balance * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        profit_loss = balance - initial_balance
        win_rate = (win_trades / total_trades) * 100 if total_trades > 0 else 0

        result = {
            "strategy_id": id,
            "total_trades": total_trades,
            "profit_loss": round(profit_loss, 2),
            "win_rate": round(win_rate, 2),
            "max_drawdown": round(max_drawdown, 2)
        }

        return result, 200
