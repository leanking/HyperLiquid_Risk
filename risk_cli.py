from risk import RiskManager, Position, Side
from typing import Optional
import cmd
import json

class RiskManagerCLI(cmd.Cmd):
    intro = 'Welcome to the Risk Management System. Type help or ? to list commands.\n'
    prompt = '(risk) '

    def __init__(self):
        super().__init__()
        self.risk_manager: Optional[RiskManager] = None
        self.initial_equity = 0.0

    def do_init(self, arg):
        """
        Initialize risk manager with: account_equity [max_position_size_usd] [max_leverage] [max_drawdown_pct] [max_position_pct]
        Example: init 10000 50000 10 15 20
        """
        args = arg.split()
        try:
            account_equity = float(args[0])
            max_position_size_usd = float(args[1]) if len(args) > 1 else 100000
            max_leverage = float(args[2]) if len(args) > 2 else 10
            max_drawdown_pct = float(args[3]) if len(args) > 3 else 15
            max_position_pct = float(args[4]) if len(args) > 4 else 20

            self.risk_manager = RiskManager(
                account_equity=account_equity,
                max_position_size_usd=max_position_size_usd,
                max_leverage=max_leverage,
                max_drawdown_pct=max_drawdown_pct,
                max_position_pct=max_position_pct
            )
            self.initial_equity = account_equity
            print(f"Risk manager initialized with equity: ${account_equity:,.2f}")
        except (IndexError, ValueError):
            print("Error: Please provide valid numbers for initialization")

    def do_add_position(self, arg):
        """
        Add a position: symbol side size entry_price leverage [liquidation_price]
        Example: add_position BTC-USDT LONG 0.1 50000 5 45000
        """
        if not self.risk_manager:
            print("Please initialize the risk manager first using 'init'")
            return

        args = arg.split()
        try:
            symbol = args[0]
            side = Side[args[1].upper()]
            size = float(args[2])
            entry_price = float(args[3])
            leverage = float(args[4])
            liquidation_price = float(args[5]) if len(args) > 5 else None

            position = Position(
                symbol=symbol,
                side=side,
                size=size,
                entry_price=entry_price,
                leverage=leverage,
                liquidation_price=liquidation_price
            )

            if self.risk_manager.add_position(position):
                print(f"Position added successfully: {symbol} {side.value}")
            else:
                print("Position rejected: Exceeds risk parameters")
        except (IndexError, ValueError) as e:
            print(f"Error: Please provide valid position details - {str(e)}")

    def do_portfolio_metrics(self, arg):
        """Show current portfolio metrics"""
        if not self.risk_manager:
            print("Please initialize the risk manager first using 'init'")
            return

        metrics = self.risk_manager.calculate_portfolio_metrics()
        print(json.dumps(metrics, indent=2))

    def do_position_risk(self, arg):
        """
        Calculate position risk: symbol current_price
        Example: position_risk BTC-USDT 51000
        """
        if not self.risk_manager:
            print("Please initialize the risk manager first using 'init'")
            return

        args = arg.split()
        try:
            symbol = args[0]
            current_price = float(args[1])

            for position in self.risk_manager.positions:
                if position.symbol == symbol:
                    risk_metrics = self.risk_manager.calculate_position_risk(position, current_price)
                    print(json.dumps(risk_metrics, indent=2))
                    return
            print(f"No position found for symbol: {symbol}")
        except (IndexError, ValueError):
            print("Error: Please provide valid symbol and current price")

    def do_check_drawdown(self, arg):
        """Check current drawdown status"""
        if not self.risk_manager:
            print("Please initialize the risk manager first using 'init'")
            return

        drawdown_info = self.risk_manager.check_drawdown(self.initial_equity)
        print(json.dumps(drawdown_info, indent=2))

    def do_suggest_size(self, arg):
        """
        Get suggested position size: price leverage
        Example: suggest_size 50000 5
        """
        if not self.risk_manager:
            print("Please initialize the risk manager first using 'init'")
            return

        args = arg.split()
        try:
            price = float(args[0])
            leverage = float(args[1])
            suggested_size = self.risk_manager.suggest_position_size(price, leverage)
            print(f"Suggested position size: {suggested_size:.8f}")
        except (IndexError, ValueError):
            print("Error: Please provide valid price and leverage")

    def do_list_positions(self, arg):
        """List all current positions"""
        if not self.risk_manager:
            print("Please initialize the risk manager first using 'init'")
            return

        if not self.risk_manager.positions:
            print("No positions currently open")
            return

        for pos in self.risk_manager.positions:
            print(f"\nSymbol: {pos.symbol}")
            print(f"Side: {pos.side.value}")
            print(f"Size: {pos.size}")
            print(f"Entry Price: ${pos.entry_price:,.2f}")
            print(f"Leverage: {pos.leverage}x")
            if pos.liquidation_price:
                print(f"Liquidation Price: ${pos.liquidation_price:,.2f}")
            print(f"Unrealized PnL: ${pos.unrealized_pnl:,.2f}")

    def do_quit(self, arg):
        """Exit the risk management system"""
        print("Exiting Risk Management System")
        return True

if __name__ == '__main__':
    RiskManagerCLI().cmdloop() 