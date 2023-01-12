import datetime
import numpy as np
import requests
import time

class Bot():
    def __init__(self, pair: str, balances: list[float]) -> None:
        self.balances = balances
        self.order_book = None
        self.pair = pair
        self.orders = {}
        self.last_show_balances_ts = datetime.datetime.utcnow() + datetime.timedelta(seconds=-30)
        self.force_fetch_orderbook = False

    def fetch_orderbook(self) -> None:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        params = {
            "symbol": self.pair,
            "precision": "P0",
            "length": 25,
        }

        url = f'https://api.rhino.fi/market-data/book/{params["symbol"]}/{params["precision"]}/{params["length"]}'

        try:
            response = requests.request(
                "GET",
                url,
                headers=headers,
            )
        except requests.exceptions.Timeout as e:
            print(e)
            if self.order_book is None:
                self.force_fetch_orderbook = True
                return
        except requests.exceptions.RequestException as e:
            raise SystemExit(e)
        
        if response.status_code == 200:
            res = response.json()
            self.order_book = {'bids': res[:params["length"]], 'asks': res[params["length"]+1:]}
        else:
            print(response.text)
        
    @property
    def best_orders(self):
        return {k: v[0] for k, v in self.order_book.items()}
    
    def show_balances(self):
        self.last_show_balances_ts = datetime.datetime.utcnow()
        print(self.last_show_balances_ts, f'CURRENT BALANCES: {self.pair.split(":")[0]} {"{:.4f}".format(self.balances[0])} {self.pair.split(":")[1]} {"{:.4f}".format(self.balances[1])}')

    def generate_order_specs(self, range=.05, size=5):
        for k, v in self.best_orders.items():
            best_price = v[0]
            best_amt = v[2]
            order_prices = np.random.uniform(low=best_price*(1-range), high=best_price*(1+range), size=(size,)).tolist()
            order_amts = np.random.uniform(low=best_amt*(1-range), high=best_amt*(1+range), size=(size,)).tolist()
            self.orders[k] = [[price, amt] for price, amt in zip(order_prices, order_amts)]
            
    def place_orders(self):
        for order_type, order_list in self.orders.items():
            for order in order_list:
                print(datetime.datetime.utcnow(), f'PLACE {order_type[:-1].upper()} @ {"{:.4f}".format(order[0])} {"{:.4f}".format(abs(order[1]))}')
                
    def check_filled(self):
        best_orders = self.best_orders
        for order_type in self.orders:
            best_price = best_orders[order_type][0]
            remove_orders = []
            for i in range(len(self.orders[order_type])):
                order = self.orders[order_type][i]
                order_price = order[0]
                filled = (order_type == 'bids' and order_price > best_price) or (order_type == 'asks' and order_price < best_price)
                if filled:
                    # check if enough balance to pay for order, otherwise cancel
                    if (order_type == 'bids' and order[0] * order[1] > self.balances[1]) or (order_type == 'asks' and abs(order[1]) > self.balances[0]):
                        remove_orders.append(i)  # cancel order and go to the next one
                        print(datetime.datetime.utcnow(), f'CANCELLED {order_type[:-1].upper()} @ {"{:.4f}".format(order[0])} {"{:.4f}".format(abs(order[1]))}')
                        continue 
                    balances_changes = [order[1], -order[0] * order[1]]
                    print(datetime.datetime.utcnow(), f'FILLED {order_type[:-1].upper()} @ {"{:.4f}".format(order[0])} {"{:.4f}".format(abs(order[1]))} ({self.pair.split(":")[0]} {"{:.4f}".format(balances_changes[0])} {self.pair.split(":")[1]} {"{:.4f}".format(balances_changes[1])})')
                    remove_orders.append(i)

                    self.balances = [x + y for x, y in zip(self.balances, balances_changes)]
            self.orders[order_type] = [o for i, o in enumerate(self.orders[order_type]) if i not in remove_orders]
    
    
if __name__ == "__main__":
    bot = Bot(pair="ETH:USDT", balances=[10, 2000])
    while True:
        bot.fetch_orderbook()
        if bot.force_fetch_orderbook:
            time.sleep(5)
            continue
        bot.generate_order_specs()
        bot.place_orders()
        bot.check_filled()
        if datetime.datetime.utcnow() > bot.last_show_balances_ts + datetime.timedelta(seconds=30):
            bot.show_balances()
        time.sleep(5)