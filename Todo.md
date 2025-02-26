## TODO

#### ~~Save logs and images for debugging~~ 
* ~~logs~~
* ~~Images~~


#### ~~Support hassio classes~~ 
* ~~device_class~~
* ~~unit_of_measurement~~

#### Upload images to improve AI model

* https://github.com/jomjol/AI-on-the-edge-device/discussions/3551

#### Implement remote call for flow_start
const.py already setup : 
* DEFAULT_SCAN_INTERVAL = 300
* DEFAULT_FLOW_ROUND_TIME_WAIT = 30 
Need to call API_flow_start in sensor.py, wait and get values

#### Better error handling if Neg rate or too High rate
* sensor.py L 227 : Set prevalue on error
