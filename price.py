#!/usr/bin/env python3

from flask import Flask, request, abort
from r2r_offer_utils import normalization
from exchangeratesapi import Api
import json
import redis
import rejson

TRIAS_INPUT     = 0 # TRIAS
ROUTERANK_INPUT = 1 # ROUTERANK
VERBOSE         = 1

def price_to_eur(currency="EUR", price=0):
    if currency == "EUR":
        return price
    if price is None:
        return None

    currency_api = Api()
    # IF the currency is not known
    # TODO: standardize error output among all our TRIAS R2R codes
    if not currency_api.is_currency_supported(currency):
        print("Unsupported currency: ", currency)
        return -1
    # convert the currency
    rate = currency_api.get_rate(base=currency, target='EUR')
    return round(rate * price)



app = Flask(__name__)
@app.route('/compute', methods=['POST'])
def extract():
    # import ipdb; ipdb.set_trace()

    data       = request.get_json()
    request_id = data['request_id']
    response   = app.response_class(
        response='{{"request_id": "{}"}}'.format(request_id),
        status=200,
        mimetype='application/json'
    )

    if VERBOSE== 1:
        print("price-fc start")
        print("request_id = " + request_id)
        print("______________________________")

    if TRIAS_INPUT == 1:
        # ask for the entire list of offer ids
        offer_data_1 = cache.mget('{}:offers'.format(request_id))
        # TODO


    if ROUTERANK_INPUT == 1:
        # extract required offer data from cache
        offer_ids            = []
        offer_currency       = {}
        offer_bookable_total = {}
        offer_complete_total = {}

        offer_data_1 = cache.jsonget('{}:offers'.format(request_id))
        if not(offer_data_1 is None):
            for offer in offer_data_1:
                if VERBOSE == 1:
                    print("offer = " + offer)
                key_currency       = request_id + ":" + offer + ":" + "currency"
                key_bookable_total = request_id + ":" + offer + ":" + "bookable_total"
                key_complete_total = request_id + ":" + offer + ":" + "complete_total"

                currency = cache.jsonget(key_currency)
                if VERBOSE == 1:
                    if not(currency is None):
                        print("currency = " + currency)
                    else:
                        print("currency = None")

                bookable_total = cache.jsonget(key_bookable_total)
                if VERBOSE == 1:
                    if not(bookable_total is None):
                        print("bookable_total = " + str(bookable_total))
                    else:
                        print("bookable_total = None")

                complete_total = cache.jsonget(key_complete_total)
                if VERBOSE == 1:
                    if not(complete_total is None):
                        print("complete_total = " + str(complete_total))
                    else:
                        print("complete_total = None")
                offer_ids.append(offer)
                offer_currency[offer]         = currency
                offer_bookable_total[offer]   = price_to_eur(currency, bookable_total)
                offer_complete_total[offer]   = price_to_eur(currency, complete_total)
            if VERBOSE == 1:
                print("offer_ids            = " + str(offer_ids))
                print("offer_currency       = " + str(offer_currency))
                print("offer_bookable_total = " + str(offer_bookable_total))
                print("offer_complete_total = " + str(offer_complete_total))

    # print all keys
    #for key in cache.scan_iter():
    #   print(key)


    offer_complete_total_z_scores = normalization.zscore(offer_complete_total)
    print("offer_complete_total_z_scores = " + str(offer_complete_total_z_scores))
    if VERBOSE == 1:
        print("price-fc end")
    return response


if __name__ == '__main__':
    import os

    FLASK_PORT = 5000
    REDIS_HOST = 'localhost'
    REDIS_PORT = 6379

    os.environ["FLASK_ENV"] = "development"
    if TRIAS_INPUT == 1:
        cache         = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

    if ROUTERANK_INPUT == 1:
        cache         = rejson.Client(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

    print("launching FLASK APP")
    app.run(port=FLASK_PORT, debug=True)

    exit(0)


# some valid request=ids in rejson
# insert #1000 (request_id: #25:17988)
# insert #2000 (request_id: #24:27682)
# insert #3000 (request_id: #22:13232)
# insert #4000 (request_id: #25:26156)
# insert #5000 (request_id: #24:13701)
# insert #6000 (request_id: #25:29833)
# insert #7000 (request_id: #25:11699)
# insert #8000 (request_id: #24:6890)
# insert #9000 (request_id: #25:3193)
# insert #10000 (request_id: #24:10239)
# insert #11000 (request_id: #23:21757)
# insert #12000 (request_id: #23:27523)
# insert #13000 (request_id: #23:6310)
# insert #14000 (request_id: #22:9449)
# insert #15000 (request_id: #24:16769)
# insert #16000 (request_id: #25:4647)
