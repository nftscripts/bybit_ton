from loguru import logger
from math import floor
from pybit import spot
from pybit.exceptions import InvalidRequestError
from time import (
    time,
    sleep,
)
from config import (
    coin,
)


class CoinSeller:
    def __init__(self, api_key: str, api_secret: str, proxy: str) -> None:
        self.session_auth = spot.HTTP(
            endpoint='https://api.bybit.com',
            api_key=api_key,
            api_secret=api_secret)
        self.session_auth.client.proxies.update({'https': proxy, 'http': proxy})

    def run(self) -> None:
        self.check_balance()

    def check_balance(self) -> None:
        balance_request = self.session_auth.get_wallet_balance()
        names = [name['coinName'] for name in balance_request['result']['balances']]
        balance_check = [balance['total'] for balance in balance_request['result']['balances']]
        zip_balances = list(zip(names, balance_check))
        logger.info(zip_balances)
        logger.info('Checking balance...')
        for name, balance in zip_balances:
            if name == 'USDT' and float(balance) > 1:
                logger.info(f'{balance} USDT')
                self.buy_tokens(balance)
            else:
                logger.info('There is not USDT on your balance')

    def sell_tokens(self, balance: str, price: float) -> None:
        n_digits = 2
        factor = 10 ** n_digits
        try:
            qty = floor(float(balance) * factor) / factor
            req = self.session_auth.place_active_order(
                symbol=f'{coin}USDT',
                side='Sell',
                type='LIMIT',
                price=price,
                qty=qty,
                timeInForce="GTC",
                recvWindow=10000)
            order_id = req['result']['orderId']
            logger.info(f'Placed order {coin} for price: {price} USDT')
            self.check_order_after_selling(order_id)

        except InvalidRequestError as ex:
            logger.error(f'Something went wrong | {ex}')

    def buy_tokens(self, usdt_balance: float) -> None:
        n_digits = 2
        factor = 10 ** n_digits
        try:
            qty = floor(float(usdt_balance) * factor) / factor
            req = self.session_auth.place_active_order(
                symbol=f'{coin}USDT',
                side='Buy',
                type='Market',
                qty=qty,
                timeInForce="GTC",
                recvWindow=10000)

            order_id = req['result']['orderId']
            logger.info(f'Bought {coin}')
            price = self.check_price(order_id)
            self.check_balance_after_buying(price)

        except InvalidRequestError as ex:
            logger.error(f'Something went wrong | {ex}')

    def check_order_after_selling(self, order_id: int) -> None:
        now = time()
        try:
            while True:
                sleep(1)
                req = self.session_auth.query_active_order()
                is_working = [is_working['isWorking'] for is_working in req['result']]
                if is_working[0] is True and time() - now < 60:
                    logger.info('Order is still ongoing')
                    continue
                else:
                    self.cancel_order(order_id)
                    break

        except Exception as ex:
            logger.info(ex)
            self.run()

    def cancel_order(self, order_id: int) -> None:
        try:
            logger.info('Deleting order')
            self.session_auth.cancel_active_order(orderId=order_id)
            logger.info('Order deleted')
            self.check_balance_after_cancelling()
        except Exception as ex:
            logger.info(f'Something went wrong | {ex}')
            self.check_balance_after_cancelling()

    def check_balance_after_cancelling(self) -> None:
        balance_request = self.session_auth.get_wallet_balance()
        names = [name['coinName'] for name in balance_request['result']['balances']]
        balance_check = [balance['total'] for balance in balance_request['result']['balances']]
        zip_balances = list(zip(names, balance_check))
        logger.info(zip_balances)
        logger.info('Checking balance...')
        for name, balance in zip_balances:
            if name == coin and float(balance) > 1:
                logger.info(f'{balance, coin}')
                self.sell_market_price(balance)

    def sell_market_price(self, balance: float) -> None:
        n_digits = 2
        factor = 10 ** n_digits
        try:
            qty = floor(float(balance) * factor) / factor
            req = self.session_auth.place_active_order(
                symbol=f'{coin}USDT',
                side='Sell',
                type='Market',
                qty=qty,
                timeInForce="GTC",
                recvWindow=10000)
            self.run()
        except Exception as ex:
            logger.error(ex)

    def check_price(self, order_id: int) -> float:

        req = self.session_auth.user_trade_records(orderId=order_id)
        results = req['result']
        price = [price['price'] for price in results]
        return price[0]

    def check_balance_after_buying(self, price: float) -> None:
        balance_request = self.session_auth.get_wallet_balance()
        names = [name['coinName'] for name in balance_request['result']['balances']]
        balance_check = [balance['total'] for balance in balance_request['result']['balances']]
        zip_balances = list(zip(names, balance_check))
        logger.info(zip_balances)
        logger.info('Checking balance...')
        for name, balance in zip_balances:
            if name == coin and float(balance) > 1:
                logger.info(f'{balance, coin}')
                self.sell_tokens(balance, price)
