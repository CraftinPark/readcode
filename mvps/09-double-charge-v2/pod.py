"""One request handled by one pod process, then the process exits.

    python pod.py pay ORDER_ID REQUEST_ID [CARD]
"""
import sys

from shop import checkout

if __name__ == "__main__":
    args = sys.argv[1:]
    card = args[3] if len(args) > 3 else "4242424242424242"
    print(checkout.pay(int(args[1]), args[2], card))
