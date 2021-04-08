#!/usr/bin/env python3
import os
import pathlib
import logging
import configparser as cp
import isodate
import redis

from r2r_offer_utils  import normalization
from r2r_offer_utils  import cache_operations
from r2r_offer_utils.logging import setup_logger
from exchangeratesAPI.exchange_rates import exchange_rates
from flask            import Flask, request


service_name = os.path.splitext(os.path.basename(__file__))[0]
#############################################################################
#############################################################################
#############################################################################
# init Flask
app          = Flask(service_name)
#############################################################################
#############################################################################
#############################################################################
# init config
config = cp.ConfigParser()
config.read(f'{service_name}.conf')
#############################################################################
#############################################################################
#############################################################################
# init cache
cache = redis.Redis(host=config.get('cache', 'host'),
                    port=config.get('cache', 'port'))
#############################################################################
#############################################################################
#############################################################################
# init logging
logger, ch = setup_logger()

VERBOSE = int(str(pathlib.Path(config.get('running', 'verbose'))))
SCORES  = str(pathlib.Path(config.get('running',  'scores')))

#############################################################################
#############################################################################
#############################################################################
# init external service for exchange rates
currency_api = exchange_rates()
#############################################################################
#############################################################################
#############################################################################

def price_to_eur(currency="EUR", price=0.0):
    if currency == "EUR":
	    return price
    if price is None:
	    return None
    try:
        # if the currency is not known
        if not currency_api.is_currency_supported(currency):
            logging.warning("Unsupported currency in price-fc: {}".format(currency))
            return None
        # convert the currency
        rate = currency_api.get_rate(currency)
    except:
        logging.warning("External service exchangeratesapi failed in price-fc.")
        return None
    if rate > 0:
        return round(price/rate)
    else:
        return None
#############################################################################
#############################################################################
#############################################################################
# A method listing out on the screen all keys that are in the cache.
@app.route('/test', methods=['POST'])
def test():
    data       = request.get_json()
    request_id = data['request_id']

    print("Listing cache.")
    for key in cache.scan_iter():
       print(key)

    response   = app.response_class(
        response ='{{"request_id": "{}"}}'.format(request_id),
        status   =200,
        mimetype  ='application/json'
    )
    return response
#############################################################################
#############################################################################
#############################################################################
# A method executing computations assigned to the price-fc feature collector. The price-fc feature collector is
# responsible for computation of the following determinant factors: "total_price", "ticket_coverage" and
# "can_share_cost".
#
# Computation is composed of four phases:
# Phase I:   Extraction of data required by price-fc feature collector from the cache. A dedicated procedure defined for
#            this purpose in the unit "cache_operations.py" is utilized.
# Phase II:  Use the external service to convert prices to EUR (if needed). A class collecting external data has been
#            implemented in the module "exchange_rates.py".
# Phase III: Compute values of weights assigned to price-fc. For aggregation of data at the tripleg level and for
#            normalization of weights a dedicated procedure implemented in the unit "normalization.py" are utilized.
#            By default "z-scores" are used to normalize data.
# Phase IV:  Storing the results produced by price-fc to cache. A dedicated procedure defined for
# #          this purpose in the unit "cache_operations.py" is utilized.

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
        print("______________________________")
        print("price-fc start")
        print("request_id = " + request_id)
    #
    # I. extract data required by price-fc from cache
    #
    try:
        output_offer_level, output_tripleg_level = cache_operations.read_data_from_cache_wrapper(
            cache,
            request_id,
            ["bookable_total", "complete_total"],
            ["duration", "can_share_cost"])
    except redis.exceptions.ConnectionError as exc:
        logging.debug("Reading from cache by price-fc feature collector failed.")
        response.status_code = 424
        return response

    if VERBOSE == 1:
        print("output_offer_level   = " + str(output_offer_level))
        print("output_tripleg_level = " + str(output_tripleg_level))

    #
    # II. use the external service to convert prices to EUR
    #
    if "offer_ids" in output_offer_level.keys():
        for offer in output_offer_level["offer_ids"]:
            # complete_total
            output_offer_level[offer]["complete_total_EUR"] = price_to_eur(output_offer_level[offer]["complete_total"]["currency"], int(output_offer_level[offer]["complete_total"]["value"]))
            # boobkable_total
            output_offer_level[offer]["bookable_total_EUR"] = price_to_eur(output_offer_level[offer]["bookable_total"]["currency"], int(output_offer_level[offer]["bookable_total"]["value"]))
    #
    # III. compute values assigned to price-fc
    #
    # compute ticket_coverage and prepare data for calculation of scores
    ticket_coverage      = {}
    offer_bookable_total = {}
    offer_complete_total = {}
    if "offer_ids" in output_offer_level.keys():
        for offer in output_offer_level["offer_ids"]:
            offer_bookable_total[offer] = output_offer_level[offer]["bookable_total_EUR"]
            offer_complete_total[offer] = output_offer_level[offer]["complete_total_EUR"]
            if (output_offer_level[offer]["bookable_total_EUR"] is not None) and (output_offer_level[offer]["complete_total_EUR"] is not None) and (output_offer_level[offer]["complete_total_EUR"] > 0):
                ticket_coverage[offer] = output_offer_level[offer]["bookable_total_EUR"]/output_offer_level[offer]["complete_total_EUR"]

    # process can_share_cost (aggregate can_share_cost over triplegs using duration information)
    can_share_cost = {}
    if "offer_ids" in output_offer_level.keys():
        for offer in output_offer_level["offer_ids"]:
            if "triplegs" in output_tripleg_level[offer].keys():
                triplegs = output_tripleg_level[offer]["triplegs"]
                temp_duration = {}
                temp_can_share_cost = {}
                for tripleg in triplegs:
                    ttemp_duration                = output_tripleg_level[offer][tripleg]["duration"]
                    ttemp_can_share_cost          = output_tripleg_level[offer][tripleg]["can_share_cost"]
                    temp_duration[tripleg]        = isodate.parse_duration(ttemp_duration).seconds
                    temp_can_share_cost[tripleg]  = ttemp_can_share_cost
                can_share_cost[offer] = normalization.aggregate_a_quantity_over_triplegs(triplegs, temp_duration, temp_can_share_cost)


    # calculate scores
    if SCORES == "minmax_scores":
        # calculate minmax scores
        offer_complete_total_scores        = normalization.minmaxscore(offer_complete_total, flipped=True)
        ticket_coverage_scores             = normalization.minmaxscore(ticket_coverage)
        can_share_cost_scores              = normalization.minmaxscore(can_share_cost)
    else:
        # by default z-scores are calculated
        offer_complete_total_scores        = normalization.zscore(offer_complete_total, flipped=True)
        ticket_coverage_scores             = normalization.zscore(ticket_coverage)
        can_share_cost_scores              = normalization.zscore(can_share_cost)

    if VERBOSE == 1:
        print("offer_complete_total_z_scores      = " + str(offer_complete_total_scores))
        print("ticket_coverage_zscores            = " + str(ticket_coverage_scores ))
        print("can_share_cost_zscores             = " + str(can_share_cost_scores))
    #
    # IV. store the results produced by price-fc to cache
    #
    try:
        cache_operations.store_simple_data_to_cache_wrapper(cache, request_id, offer_complete_total_scores,
                                                            "total_price")
        cache_operations.store_simple_data_to_cache_wrapper(cache, request_id, ticket_coverage_scores,
                                                            "ticket_coverage")
        cache_operations.store_simple_data_to_cache_wrapper(cache, request_id, can_share_cost_scores,
                                                            "can_share_cost")
    except redis.exceptions.ConnectionError as exc:
        logging.debug("Writing outputs to cache by price-fc feature collector failed.")

    if VERBOSE == 1:
        print("price-fc end")
        print("______________________________")
    return response
#############################################################################
#############################################################################
#############################################################################

if __name__ == '__main__':
    import os

    FLASK_PORT = 5001
    REDIS_HOST = 'localhost'
    REDIS_PORT = 6379
    os.environ["FLASK_ENV"] = "development"
    cache        = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    app.run(port=FLASK_PORT, debug=True, use_reloader=False)
    exit(0)
