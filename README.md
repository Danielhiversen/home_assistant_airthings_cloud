# Airthings cloud
![Validate with hassfest](https://github.com/Danielhiversen/home_assistant_airthings_cloud/workflows/Validate%20with%20hassfest/badge.svg)
[![GitHub Release][releases-shield]][releases]
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

Custom component for using [Airthings](https://www.airthings.com//) sensors in Home Assistant.

[Support the developer](http://paypal.me/dahoiv)


## Install
Use [hacs](https://hacs.xyz/) or copy the files to the custom_components folder in Home Assistant config.

## Configuration 
In configuration.yaml:

```
sensor:
  - platform: airthings_cloud
    username: mail@test.com
    password: YOURPSWD
```


[releases]: https://github.com/Danielhiversen/home_assistant_airthings_cloud/releases
[releases-shield]: https://img.shields.io/github/release/Danielhiversen/home_assistant_airthings_cloud.svg?style=popout
[downloads-total-shield]: https://img.shields.io/github/downloads/Danielhiversen/home_assistant_airthings_cloud/total
[hacs-shield]: https://img.shields.io/badge/HACS-Default-orange.svg
[hacs]: https://hacs.xyz/docs/default_repositories

