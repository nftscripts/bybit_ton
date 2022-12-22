from multiprocessing import Process, freeze_support
from config import instances
from coin_seller import CoinSeller


def main() -> None:
    freeze_support()
    for instance in instances:
        coin_seller = CoinSeller(**instance)
        process = Process(target=coin_seller.run)
        process.start()


if __name__ == '__main__':
    main()
