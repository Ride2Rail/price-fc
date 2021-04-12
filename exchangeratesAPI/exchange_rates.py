import datetime
import requests
import logging

# class implementing external service providing access to exchange rates published by the European Central Bank on the
# site http://www.ecb.int/stats/eurofxref/eurofxref-daily.xml
class exchange_rates:
    # dictionary of exchange rates
    rates = {}
    # datetime when the dictionary was created/updated
    date  = None
    #############################################################################
    #############################################################################
    #############################################################################

    # Constructor reading exchange rates from the ECB website and compiling dictionary of exchange rates
    def __init__(self):
        rates = {}
        date  = None
        self.read_data()
    #############################################################################
    #############################################################################
    #############################################################################

    # Procedure reading exchange rates from the ECB website and compiling dictionary of exchange rates
    def read_data(self):
        from xml.etree import cElementTree as ET

        self.date = datetime.datetime.now()
        try:
            r    = requests.get('http://www.ecb.int/stats/eurofxref/eurofxref-daily.xml', stream=True)
        except requests.exceptions.RequestException as e:
            logging.warning("External service could not read exchange rates from http://www.ecb.int.")
            return None
        tree = ET.parse(r.raw)
        root = tree.getroot()

        for child in root:
            for subchild in child:
                for subsubchild in subchild:
                    self.rates[subsubchild.attrib['currency']] = float(subsubchild.attrib['rate'])
    #############################################################################
    #############################################################################
    #############################################################################

    # Procedure returning True is a currency is supported and False otherwise
    def is_currency_supported(self, currency):
        if currency not in self.rates:
            return False
        else:
            return True
    #############################################################################
    #############################################################################
    #############################################################################

    # Procedure returning exchange rate for a currency that is given as an argument
    def get_rate(self, currency):
        now = datetime.datetime.now()
        if (self.date.year != now.year) or (self.date.month != now.month) or (self.date.day != now.day):
            self.read_data()
        if self.is_currency_supported(currency):
            return self.rates[currency]
        else:
            return -1
    #############################################################################
    #############################################################################
    #############################################################################

    # Procedure printing the dictionary with exchange rates on the screen
    def print(self):
        print(self.rates)

    #############################################################################
    ###########################################################################
    #############################################################################
