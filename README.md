# price-fc
# Price feature collector


## Usage

### Local development (debug on)

```bash
$ python3 price.py
 * Serving Flask app "price" (lazy loading)
 * Environment: development
 * Debug mode: on
 * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)
 * Restarting with stat
 * Debugger is active!
 * Debugger PIN: 441-842-797
```

### Local development (debug off
```bash
$ FLASK_APP='price.py' flask run)
 * Serving Flask app "price.py"
 * Environment: production
   WARNING: This is a development server. Do not use it in a production deployment.
   Use a production WSGI server instead.
 * Debug mode: off
 * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)
```

### Example Request

```bash
$ curl --header 'Content-Type: application/json' \
       --request POST  \
       --data '{"request_id": "123x" }' \
         http://localhost:5000/compute
{"request_id": "123x"}%
```



## Api for currencies:
[https://pypi.org/project/python-exchangeratesapi/](https://pypi.org/project/python-exchangeratesapi/)
