CREATE TABLE IF NOT EXISTS pickup_windows (
    window_start timestamp NOT NULL,
    window_end timestamp NOT NULL,
    pickup_location_id integer NOT NULL,
    num_trips bigint NOT NULL,
    PRIMARY KEY(window_start, pickup_location_id)
);
CREATE TABLE IF NOT EXISTS pickup_sessions (
    window_start timestamp NOT NULL,
    window_end timestamp NOT NULL,
    pickup_location_id integer NOT NULL,
    num_trips bigint NOT NULL,
    PRIMARY KEY(window_start, pickup_location_id)
);
CREATE TABLE IF NOT EXISTS hourly_tips (
    window_start timestamp PRIMARY KEY,
    window_end timestamp NOT NULL,
    total_tip numeric(18,2) NOT NULL,
    num_trips bigint NOT NULL
);
