# Feature collector "price-fc"
***Version:*** 1.0

***Date:*** 14.04.2021

***Authors:***  [Ľuboš Buzna](https://github.com/lubos31262); [Milan Straka](https://github.com/bioticek)

***Address:*** University of Žilina, Univerzitná 8215/1, 010 26 Žilina, Slovakia
# Description 

The "price-fc" feature collector is  a module of the **Ride2Rail Offer Categorizer** responsible for the computation of the following determinant factors: ***"total_price"***, ***"ticket_coverage"*** and
 ***"can_share_cost"***.

**Computation is composed of four phases:**

***Phase I:***   Extraction of data required by price-fc feature collector from the cache. A dedicated procedure defined for
            this purpose from the unit ***"[cache_operations.py](https://github.com/Ride2Rail/r2r-offer-utils/wiki/cache_operations.py)"*** is utilized.

***Phase II:***  Use of the external service to convert prices to EUR (if needed). A class collecting external data has been
            implemented in the module ***"[exchange_rates.py](https://github.com/Ride2Rail/price-fc/wiki/exchange_rates.py)"***.

***Phase III:*** Computation of weights assigned to "price-fc" feature collector. For the aggregation of data at the tripleg level and for
            normalization of weights a dedicated procedure implemented in the unit ***"[normalization.py](https://github.com/Ride2Rail/r2r-offer-utils/wiki/normalization.py)"*** are utilized. By default "z-scores" are used to normalize data.



***Phase IV:*** Storing of the results produced by "price-fc" to cache. A dedicated procedure defined for
            this purpose in the unit ***"[cache_operations.py](https://github.com/Ride2Rail/r2r-offer-utils/wiki/cache_operations.py)"*** is utilized.

# Configuration

The following values of parameters can be defined in the configuration file ***"price.conf"***.

Section ***"running"***:
- ***"verbose"*** - if value __"1"__ is used, then feature collector is run in the verbose mode,
- ***"scores"*** - if  value __"minmax_score"__ is used, the minmax approach is used for normalization of weights, otherwise, the __"z-score"__ approach is used. 

Section ***"cache"***: 
- ***"host"*** - host address where the cache service that should be accessed by ***"price-fc"*** feature collector is available
- ***"port"*** - port number where the cache service that should be accessed used by ***"price-fc"*** feature collector is available

**Example of the configuration file** ***"price.conf"***:
```bash
[service]
name = price
type = feature collector
developed_by = Lubos Buzna <https://github.com/lubos31262> and Milan Straka <https://github.com/bioticek>

[running]
verbose = 1
scores  = minmax_scores

[cache]
host = cache
port = 6379
```

# Usage
### Local development (debug on)
```bash
$ python3 price.py
 * Serving Flask app "price" (lazy loading)
 * Environment: development
 * Debug mode: on
 * Running on http://127.0.0.1:5001/ (Press CTRL+C to quit)
 * Restarting with stat
 * Debugger is active!
 * Debugger PIN: 441-842-797
```

### Example Request
```bash
$ curl --header 'Content-Type: application/json' \
       --request POST  \
       --data '{"request_id": "123x" }' \
         http://localhost:5001/compute
```



## API for exchange rates:
Implemented API is reading exchange rates from the service provided by the European Central Bank 
[https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml](https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml)


