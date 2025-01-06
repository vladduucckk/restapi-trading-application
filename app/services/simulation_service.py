from flask import jsonify

from app.models import Strategy


class SimulationService:
    @staticmethod
    def simulate_strategy(id, data, user):
        strategy = Strategy.query.filter_by(id=id).first()
        if not strategy or strategy.user_id != user.id:
            return jsonify(message="You can only simulate your own strategies"), 403

        total_trades, profit_loss, win_trades, max_drawdown = 0, 0.0, 0, 0.0
        initial_balance, balance, highest_balance = 10000.0, 10000.0, 10000.0

        for day in data:
            date, close_price, volume = day['date'], day['close'], day.get('volume', 1)

            buy_signal = strategy.buy_conditions['indicator'] == "momentum" and close_price > strategy.buy_conditions['threshold']
            sell_signal = strategy.sell_conditions['indicator'] == "momentum" and close_price < strategy.sell_conditions['threshold']

            if buy_signal:
                total_trades += 1
                balance -= close_price * volume

            if sell_signal:
                total_trades += 1
                balance += close_price * volume
                win_trades += 1

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

        return jsonify(result), 200