#!/usr/bin/env python3

from flask            import Flask, request, abort
from r2r_offer_utils  import normalization
from exchangeratesapi import Api
import json
import redis
import rejson
import logging
import isodate

VERBOSE         = 0
cache           = redis.Redis(host='cache', port=6379)
#############################################################################
#############################################################################
#############################################################################
def price_to_eur(currency="EUR", price=0):
    if currency == "EUR":
	    return price
    if price is None:
	    return None
    try:
        currency_api = Api()
        # IF the currency is not known
        if not currency_api.is_currency_supported(currency):
            logging.warning("Unsupported currency in price-fc: ", currency)
            return None
        # convert the currency
        rate = currency_api.get_rate(base=currency, target='EUR')
    except:
        logging.warning("External service exchangeratesapi failed in price-fc.")
        return None
    return round(rate * price)
#############################################################################
#############################################################################
#############################################################################
def extract_data_from_cache(
        request_id,
        offer_level_items,
        tripleg_level_items):

    output_offer_level_items   = {}
    output_tripleg_level_items = {}

    offer_ids  = cache.jsonget('{}:offers'.format(request_id))
    #offer_ids = cache.lrange('{}:offers'.format(request_id), 0, -1)

    output_offer_level_items["offer_ids"] = offer_ids
    if offer_ids  is not None:
        for offer in offer_ids:
            if VERBOSE == 1:
                print("offer = " + offer)
            output_offer_level_items[offer] = {}
            if len(tripleg_level_items) > 0:
                output_tripleg_level_items[offer] = {}
            for offer_level_item in offer_level_items:
                # assembly key for offer level
                temp_key  = request_id + ":" + offer + ":" + offer_level_item
                # extract offer level data from cache
                temp_data = cache.jsonget(temp_key)
                # temp_data = cache.get(temp_key)
                output_offer_level_items[offer][offer_level_item] = temp_data
                if temp_data is not None:
                    if VERBOSE == 1:
                        print(offer_level_item + " = " + str(temp_data))
                else:
                    if VERBOSE == 1:
                        print(offer_level_item + " = None")
                # extract information at the tripleg level
                if len(tripleg_level_items) > 0:
                    temp_key      = request_id + ":" + offer + ":" + "legs"
                    tripleg_ids   = cache.jsonget(temp_key)
                    #tripleg_ids  = cache.get(temp_key)

                    output_tripleg_level_items[offer]["triplegs"] = tripleg_ids
                    for tripleg_id in tripleg_ids:
                        print(tripleg_id)
                        output_tripleg_level_items[offer][tripleg_id] = {}
                        for tripleg_level_item in tripleg_level_items:
                            temp_key = request_id + ":" + offer + ":" + tripleg_id + ":" + tripleg_level_item
                            tripleg_data   = cache.jsonget(temp_key)
                            #tripleg_data  = cache.get(temp_key)
                            output_tripleg_level_items[offer][tripleg_id][tripleg_level_item] = tripleg_data
    return output_offer_level_items, output_tripleg_level_items
#############################################################################
#############################################################################
#############################################################################

app = Flask(__name__)
@app.route('/compute', methods=['POST'])
def extract():
    # import ipdb; ipdb.set_trace()
    data       = request.get_json()
    request_id = data['request_id']

    response   = app.response_class(
        response ='{{"request_id": "{}"}}'.format(request_id),
        status   =200,
        mimetype  ='application/json'
    )
    if VERBOSE== 1:
        print("price-fc start")
        print("request_id = " + request_id)
        print("______________________________")

    # I. extract data required by price-fc from cache
    output_offer_level, output_tripleg_level = extract_data_from_cache(
        request_id,
        ["currency", "bookable_total", "complete_total"],
        ["duration", "can_share_cost"])

    if VERBOSE== 1:
        print("output_offer_level   = " + str(output_offer_level))
        print("output_tripleg_level = " + str(output_tripleg_level))

    # II. use the external service to convert prices to EUR
    for offer in output_offer_level["offer_ids"]:
        # complete_total
        output_offer_level[offer]["complete_total"] = price_to_eur(output_offer_level[offer]["currency"], output_offer_level[offer]["complete_total"])
        # boobkable_total
        output_offer_level[offer]["bookable_total"] = price_to_eur(output_offer_level[offer]["currency"], output_offer_level[offer]["bookable_total"])

    # III. compute values assigned to price-fc
    # compute ticket_coverage and prepare data for calculation of scores
    ticket_coverage      = {}
    offer_bookable_total = {}
    offer_complete_total = {}
    for offer in output_offer_level["offer_ids"]:
        offer_bookable_total[offer] = output_offer_level[offer]["bookable_total"]
        offer_complete_total[offer] = output_offer_level[offer]["complete_total"]
        if (output_offer_level[offer]["bookable_total"] is not None) and (output_offer_level[offer]["complete_total"] is not None) and (output_offer_level[offer]["complete_total"] > 0):
            ticket_coverage[offer] = output_offer_level[offer]["bookable_total"]/output_offer_level[offer]["complete_total"]

    # process can_share_cost (aggregate can_share_cost over triplegs using duration information)
    can_share_cost = {}
    for offer in output_offer_level["offer_ids"]:
        triplegs = output_tripleg_level[offer]["triplegs"]
        temp_duration = {}
        temp_can_share_cost = {}
        for tripleg in triplegs:
            ttemp_duration                = output_tripleg_level[offer][tripleg]["duration"]
            ttemp_can_share_cost          = output_tripleg_level[offer][tripleg]["can_share_cost"]
            temp_duration[tripleg]        = isodate.parse_duration(ttemp_duration).seconds
            temp_can_share_cost[tripleg]  = ttemp_can_share_cost
        can_share_cost[offer] = normalization.aggregate_a_quantity_over_triplegs(triplegs, temp_duration, temp_can_share_cost)


    # calculate zscores
    offer_complete_total_z_scores        = normalization.zscore(offer_complete_total, flipped=True)
    ticket_coverage_z_scores             = normalization.zscore(ticket_coverage)
    can_share_cost_z_scores              = normalization.zscore(can_share_cost)

    # calculate minmaxscores
    #offer_complete_total_minmax_scores   = normalization.minmaxscore(offer_complete_total, flipped=True)
    #ticket_coverage_minmax_scores        = normalization.minmaxscore(ticket_coverage)
    #can_share_cost_minmax_scores         = normalization.minmaxscore(can_share_cost)

    if VERBOSE == 1:
        print("offer_complete_total_z_scores      = " + str(offer_complete_total_z_scores))
        print("ticket_coverage_zscores            = " + str(ticket_coverage_z_scores ))
        print("can_share_cost_zscores             = " + str(can_share_cost_z_scores))

        #print("offer_complete_total_minmax_scores = " + str(offer_complete_total_minmax_scores))
        #print("ticket_coverage_minmax_scores      = " + str(ticket_coverage_minmax_scores))
        #print("can_share_cost_minmax_scores       = " + str(can_share_cost_minmax_scores))


    # IV. store the results produced by price-fc to cache
    "total_price"
    for offer in offer_complete_total_z_scores:
        temp_key = request_id + ":" + offer + ":total_price"
        cache.set(temp_key, offer_complete_total_z_scores[offer])
    "ticket_coverage"
    for offer in ticket_coverage_z_scores:
        temp_key = request_id + ":" + offer + ":ticket_coverage"
        cache.set(temp_key, ticket_coverage_z_scores[offer])
    "can_share_cost"
    for offer in can_share_cost_z_scores:
        temp_key = request_id + ":" + offer + ":can_share_cost"
        cache.set(temp_key, can_share_cost_z_scores[offer])
    return response
#############################################################################
#############################################################################
#############################################################################

if __name__ == '__main__':
    import os

    FLASK_PORT = 5000
    REDIS_HOST = 'localhost'
    REDIS_PORT = 6379
    VERBOSE    =  1

    os.environ["FLASK_ENV"] = "development"
    #cache        = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
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

    # print all keys
    #for key in cache.scan_iter():
    #   print(key)
