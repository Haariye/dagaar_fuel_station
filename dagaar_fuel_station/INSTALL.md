# Install

```bash
cd /opt/frappe-bench
bench get-app /path/to/dagaar_fuel_station
bench --site yoursite.local install-app dagaar_fuel_station
bench --site yoursite.local migrate
bench --site yoursite.local clear-cache
bench restart
```
