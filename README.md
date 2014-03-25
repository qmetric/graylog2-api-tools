graylog2-api-tools
==================

Python Tools for Manipulating Graylog2 0.2 Rest-API

graylog2_streams.py: save, load, inspect streams

on the graylog host:
	./graylog2_streams.py -s mystreams.json
	cat mystreams.json | python -mjson.tool
<pre>
{
    "streams": [
        {
            "alert_conditions": [
                {
                    "creator_user_id": "admin",
                    "parameters": {
                        "grace": 13,
                        "threshold": 4,
                        "threshold_type": "more",
                        "time": 4
                    },
                    "type": "message_count"
                }
            ],
            "alert_receivers": {
                "emails": [
                    "bob@example.com"
                ]
            },
            "creator_user_id": "admin",
            "description": "All Mod_Security Messages",
            "rules": [
                {
                    "field": "message",
                    "inverted": false,
                    "type": 1,
                    "value": "ModSecurity: Access denied"
                }
            ],
            "title": "Mod_Security"
        }
    ],
    "total": 1
}
</pre>
------------
Or, as web requests:

curl -s http://example.com/cgi-bin/graylog2_streams.py?save=true -o /tmp/saved.json 

curl -s -X POST -H "Content-Type: application/json" -d @/tmp/saved.json http://example.com/cgi-bin/graylog2_streams.py
