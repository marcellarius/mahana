CREATE SEQUENCE seq_sample_id;


CREATE TABLE temperature_samples(
	id integer PRIMARY KEY DEFAULT nextval('seq_sample_id'),
	sensor_name text NOT NULL,
	sample_time timestamptz NOT NULL,
	temperature numeric(6,3) NOT NULL
);


CREATE INDEX ON temperature_samples(sensor_name);