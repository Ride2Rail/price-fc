#!/usr/bin/env python3

from flask import Flask, request, abort
import json
#import redis
import rejson

# from r2r_offer_utils import normalization

app = Flask(__name__)

#cache = redis.Redis(host='redis', port=6379)

@app.route('/compute', methods=['POST'])




def extract():
    # import ipdb; ipdb.set_trace()




    data = request.get_json()
    request_id = data['request_id']

    response = app.response_class(
        response='{{"request_id": "{}"}}'.format(request_id),
        status=200,
        mimetype='application/json'
    )


    print("price-fc start")


    # ask for the entire list of offer ids
    print("request_id = " + request_id)
    print("______________________________")



    # offer_data_1 = cache.mget('{}:offers'.format(request_id))

    # extract offer data
    offer_data_1 = cache.jsonget('{}:offers'.format(request_id))
    if not(offer_data_1 is None):
        for offer in offer_data_1:
            print("offer = " + offer)
            key_currency       = request_id + ":" + offer + ":" + "currency"
            key_bookable_total = request_id + ":" + offer + ":" + "bookable_total"
            key_complete_total = request_id + ":" + offer + ":" + "complete_total"

            currency = cache.jsonget(key_currency)
            if not(currency is None):
                print("currency = " + currency)
            else:
                print("currency = None")

            bookable_total = cache.jsonget(key_bookable_total)
            if not(bookable_total is None):
                print("bookable_total = " + str(bookable_total))
            else:
                print("bookable_total = None")

            complete_total = cache.jsonget(key_complete_total)
            if not(complete_total is None):
                print("complete_total = " + str(complete_total))
            else:
                print("complete_total = None")


    # print all keys
    #for key in cache.scan_iter():
    #   print(key)


    # normalization.zscore(...)
    print("price-fc end")
    return response


if __name__ == '__main__':
    import os

    FLASK_PORT = 5000
    REDIS_HOST = 'localhost'
    REDIS_PORT = 6379

    os.environ["FLASK_ENV"] = "development"

    # cache                   = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

    cache = rejson.Client(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

    print("launching FLASK APP")
    app.run(port=FLASK_PORT, debug=True)

    exit(0)
