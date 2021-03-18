 #!/usr/bin/env python3


from exchangeratesapi import Api

if __name__ == '__main__':
	api = Api()

	# Get the latest foreign exchange rates:
	api.get_rates()
	print(api.get_rates(start_date="2018-03-26"))