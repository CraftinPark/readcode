"""One pod handling one request, then exiting (like a pod that gets restarted or rescheduled).

    python pod.py pay ORDER_ID REQUEST_ID
"""
import sys

from shop import checkout

if __name__ == "__main__":
    _, cmd, order_id, request_id = sys.argv
    print(checkout.pay(int(order_id), request_id))
