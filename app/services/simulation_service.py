from app.models import Strategy


class SimulationService:
    @staticmethod
    def simulate_strategy(id, data, user_id):
        print(f"Simulating strategy {id} for user {user_id}")  # Лог для перевірки отриманих параметрів
        strategy = Strategy.query.filter_by(id=id).first()

        if not strategy:
            print(f"Strategy {id} not found.")  # Лог для перевірки, чи знайшлася стратегія
            return {"message": "Strategy not found"}, 404

        if strategy.user_id != user_id:
            print(f"User {user_id} is not authorized for strategy {id}.")  # Лог для перевірки прав доступу
            return {"message": "You can only simulate your own strategies"}, 403

        total_trades = 0  # Загальна кількість угод
        profit_loss = 0.0  # Прибуток/збиток
        win_trades = 0  # Кількість виграшних угод
        max_drawdown = 0.0  # Максимальна просадка
        initial_balance = 10000.0  # Початковий баланс
        balance = initial_balance  # Поточний баланс
        highest_balance = initial_balance  # Найвищий баланс для обчислення просадки

        # Логіка симуляції
        for day in data:
            try:
                date = day['date']
                close_price = day['close']
                volume = day.get('volume', 1)  # Якщо об'єм не вказано, за замовчуванням 1
                print(
                    f"Processing day: {date}, Close: {close_price}, Volume: {volume}")  # Лог для перевірки кожного дня
            except KeyError as e:
                print(f"Skipping day due to missing data: {day}, error: {e}")  # Лог для відлову помилок в даних
                continue

            # Логіка для сигналу покупки
            buy_signal = close_price > strategy.buy_conditions['threshold']
            # Логіка для сигналу продажу
            sell_signal = close_price < strategy.sell_conditions['threshold']

            # Логування умов сигналів для купівлі та продажу
            print(f"Buy signal: {buy_signal}, Sell signal: {sell_signal}, Close: {close_price}, "
                  f"Buy Threshold: {strategy.buy_conditions['threshold']}, Sell Threshold: {strategy.sell_conditions['threshold']}")

            # Логіка покупки
            if buy_signal:
                total_trades += 1  # Збільшуємо кількість угод
                balance -= close_price * volume  # Віднімаємо вартість покупки
                print(f"Buy on {date}: close={close_price}, volume={volume}, balance={balance}")

            # Логіка продажу
            if sell_signal:
                total_trades += 1  # Збільшуємо кількість угод
                balance += close_price * volume  # Продаємо по ціні закриття з урахуванням об'єму
                win_trades += 1
                print(f"Sell on {date}: close={close_price}, volume={volume}, balance={balance}")

            # Розрахунок максимальної просадки
            if balance > highest_balance:
                highest_balance = balance
            drawdown = (highest_balance - balance) / highest_balance * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        # Результати симуляції
        profit_loss = balance - initial_balance
        win_rate = (win_trades / total_trades) * 100 if total_trades > 0 else 0

        result = {
            "strategy_id": id,
            "total_trades": total_trades,
            "profit_loss": round(profit_loss, 2),
            "win_rate": round(win_rate, 2),
            "max_drawdown": round(max_drawdown, 2)
        }

        print(f"Simulation result: {result}")  # Лог для перевірки кінцевого результату
        return result, 200
