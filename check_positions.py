import requests
headers = {"APCA-API-KEY-ID": "PKFM75BLQPAMWVU5O5GF73B746", "APCA-API-SECRET-KEY": "3jNRT1Hh13PDkUZ87SUE3NmQXtv6WLSBLnK8C7NveVTy"}
r = requests.get("https://paper-api.alpaca.markets/v2/positions", headers=headers)
print(r.status_code)
print(r.text)
