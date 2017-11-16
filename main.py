import click
import temperusb
import datetime
import time
import threading
import json
import csv
import requests
import sys
import usb.core
import dateutil.parser

import json_encoder

@click.group()
def cli():
	pass

@cli.command()
@click.option("--post-url", help="URL to post readings to")
@click.option("--file", type=click.File(mode="w"), help="File to write output to")
@click.option("--interval", default=10, help="Interval between readings")
def monitor(post_url, interval, file):
	outputs = []
	if post_url:
		outputs.append(JSONHandler(post_url))

	if file:
		outputs.append(FileHandler(file))

	for ts, temperature in poll_temperatures(interval):
		for output in outputs:
			output(ts, temperature)

@cli.command("pushcsv")
@click.argument("input_file", type=click.File(mode="r"))
@click.argument("post_url")
def push_csv(input_file, post_url):
	json_handler = JSONHandler(post_url, batch_size=None)
	with input_file:
		reader = csv.reader(input_file)
		next(reader)
		for row in reader:
			ts = dateutil.parser.parse(row[0])
			temp = float(row[1])
			json_handler(ts, temp)
		json_handler.flush()		

class JSONHandler(object):
	def __init__(self, url, batch_size=6):
		self.url = url
		self.batch_size = batch_size
		self.data = []
		self._lock = threading.RLock()
		self._thread = None

	def _start_worker(self):
		if not self._thread:
			self._thread = threading.Thread(target=self._worker_task, daemon=True)
			self._thread.start()

	def _worker_task(self):
		while True:
			time.sleep(5)
			if self.batch_size and len(self.data) >= self.batch_size:
				self.flush()

	def flush(self):
		try:
			json_data = None
			data_values_to_send = 0
			with self._lock:
				data_values_to_send = len(self.data)
				json_data = json.dumps(self.data, cls=json_encoder.JSONEncoder)
			if json_data:
				r = requests.post(self.url, data=json_data, headers={"Content-Type": "application/json"})
				if r.status_code == requests.codes.ok:
					# If this took a while there could be extra data values waiting
					with self._lock:
						remaining_data = len(self.data) - data_values_to_send
						self.data = self.data[:remaining_data]
		except requests.exceptions.RequestException as e:
			print(e, file=sys.stderr)

	def __call__(self, timestamp, temperature):
		self._start_worker()

		with self._lock:
			self.data.append((timestamp, temperature))


class FileHandler(object):
	def __init__(self, file):
		self.file = file
		self.csv_writer = csv.writer(self.file)

	def __call__(self, timestamp, temperature):
		self.csv_writer.writerow([timestamp, temperature])
		self.file.flush()


def poll_temperatures(interval):
	while True:
		try:
			yield get_data_point()
		except usb.core.USBError as e:
			print("USB Error: " + str(e), file=sys.stderr)
		finally:
			time.sleep(interval)


def get_temperature():
	th = temperusb.TemperHandler()
	devices = th.get_devices()
	if devices:
		return devices[0].get_temperature()


def get_data_point():
	return (datetime.datetime.now(), get_temperature())


if __name__ == "__main__":
	cli()
