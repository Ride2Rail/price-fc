#!/usr/bin/env python3
import os
import sys
import pathlib
import logging
import configparser as cp

from r2r_offer_utils  import normalization
from r2r_offer_utils  import cache_operations
from exchangeratesapi import Api
import isodate

from flask            import Flask, request, abort
import redis
import rejson
import json


cache           = redis.Redis(host='cache', port=6379)

##### Config
service_basename = os.path.splitext(os.path.basename(__file__))[0]
config_file = '{name}.conf'.format(name=service_basename)
config = cp.ConfigParser()
config.read(config_file)
#####

##### Logging
# create logger
logger = logging.getLogger(service_basename)
logger.setLevel(logging.DEBUG)
# create formatter
formatter_fh = logging.Formatter('[%(asctime)s][%(levelname)s]: %(message)s')
formatter_ch = logging.Formatter('[%(asctime)s][%(levelname)s](%(name)s): %(message)s')
default_log = pathlib.Path(config.get('logging', 'default_log'))
try:
    default_log.parent.mkdir(parents=True, exist_ok=True)
    default_log.touch(exist_ok=True)

    basefh = logging.FileHandler(default_log, mode='a+')
except Exception as err:
    print("WARNING: could not create log file '{log}'"
          .format(log=default_log), file=sys.stderr)
    print("WARNING: {err}".format(err=err), file=sys.stderr)
#####

VERBOSE = int(str(pathlib.Path(config.get('running', 'verbose'))))
#############################################################################
#############################################################################
#############################################################################
def price_to_eur(currency="EUR", price=0.0):
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
app = Flask(__name__)
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
    output_offer_level, output_tripleg_level = cache_operations.extract_data_from_cache(
        cache,
        request_id,
        ["bookable_total", "complete_total"],
        ["duration", "can_share_cost"])

    if VERBOSE == 1:
        print("output_offer_level   = " + str(output_offer_level))
        print("output_tripleg_level = " + str(output_tripleg_level))

    #
    # II. use the external service to convert prices to EUR
    #
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
    for offer in output_offer_level["offer_ids"]:
        offer_bookable_total[offer] = output_offer_level[offer]["bookable_total_EUR"]
        offer_complete_total[offer] = output_offer_level[offer]["complete_total_EUR"]
        if (output_offer_level[offer]["bookable_total_EUR"] is not None) and (output_offer_level[offer]["complete_total_EUR"] is not None) and (output_offer_level[offer]["complete_total_EUR"] > 0):
            ticket_coverage[offer] = output_offer_level[offer]["bookable_total_EUR"]/output_offer_level[offer]["complete_total_EUR"]

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

    #
    # IV. store the results produced by price-fc to cache
    #
    cache_operations.store_simple_data_to_cache(cache, request_id, offer_complete_total_z_scores, "total_price")
    cache_operations.store_simple_data_to_cache(cache, request_id, ticket_coverage_z_scores, "ticket_coverage")
    cache_operations.store_simple_data_to_cache(cache, request_id, can_share_cost_z_scores, "can_share_cost")

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
    #cache        = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
    cache         = rejson.Client(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    print("launching FLASK APP")
    app.run(port=FLASK_PORT, debug=True)
    exit(0)
