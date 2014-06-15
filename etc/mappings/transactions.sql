CREATE TABLE transactions (
    id string PRIMARY KEY,
    sender string PRIMARY KEY,
    recipient string,
    amount double,
    state string,
    "timestamp" timestamp
) CLUSTERED BY (sender)
