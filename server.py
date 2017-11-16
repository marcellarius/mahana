import click
import csv
import flask
import psycopg2
import psycopg2.extras
import dateutil.parser
import datetime
from tzlocal import get_localzone
from werkzeug.local import LocalProxy
from flask import g, request, jsonify, render_template

import json_encoder


app = flask.Flask(__name__)
app.json_encoder = json_encoder.JSONEncoder


def connect_db():
    return psycopg2.connect(
        "dbname=mahana",
        cursor_factory=psycopg2.extras.NamedTupleCursor)

def get_db():
    if not hasattr(g, 'database'):
        g.database = connect_db()
    return g.database


@app.teardown_appcontext
def close_db(error):
    db_connection = getattr(g, 'database', None)
    if db_connection is None:
        return

    if error is None:
        db_connection.commit()
    else:
        db_connection.rollback()
    db_connection.close()


db = LocalProxy(get_db)


def save_datapoints(sensor_name, data_points):
    cursor = db.cursor()
    for dp in data_points:
        cursor.execute("""
            INSERT INTO temperature_samples (sensor_name, sample_time, temperature)
                VALUES (%s, %s, %s);""", 
            [sensor_name, dp[0], dp[1]]);


def get_datapoints(sensor_name):
    cursor = db.cursor()
    cursor.execute("""
        SELECT sample_time, temperature
        FROM
            (SELECT 
                sample_time, temperature,
                row_number() OVER (ORDER BY id ASC) as row_number
            FROM
                temperature_samples
            WHERE
                sensor_name = %s
            ORDER BY
                sample_time ASC) as t
        WHERE t.row_number %% 10 = 0
    """, [sensor_name])

    for row in cursor:
        yield (row.sample_time, row.temperature)

@app.route("/graph/<sensor_name>")
def graph_sensor(sensor_name):
    return render_template(
        "graph.html",
        sensor_name=sensor_name)

@app.route("/api/<sensor_name>", methods=["GET", "POST"])
def api_sensor(sensor_name):
    if request.method == "GET":
        return jsonify(list(get_datapoints(sensor_name)))
    else:
        json = request.get_json()
        save_datapoints(sensor_name, ((dateutil.parser.parse(ts).replace(tzinfo=datetime.timezone.utc), temperature) for ts, temperature in json))
        return "OK", 200

@click.group()
def cli():
    pass


@cli.command("csv")
@click.argument('sensor', type=str)
@click.argument('csvfile', type=click.File('w'))
def dump_csv(sensor, csvfile):
    local_tz = get_localzone()
    with app.app_context():
        data = get_datapoints(sensor)
        with csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(['Time', 'Temperature'])
            for ts, temp in data:
                csvwriter.writerow([ts.astimezone(local_tz).strftime("%Y-%m-%d %H:%M:%S"), temp])
        

@cli.command()
@click.option("--port", default=8900, help="The port to use")
def run(port=8900):
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
	cli()
