# Data source

New York City Open Data / 311, [311 Service Requests from 2020 to Present](https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2020-to-Present/erm2-nwe9/about_data), dataset `erm2-nwe9`.

Retrieved 14 October 2026. The CSV includes only unique key, created/closed timestamps, agency, complaint type, borough and current status. Current status is not used to infer status at the historical cutoff.

The City's [Open Data Technical Standards Manual](https://opendata.cityofnewyork.us/wp-content/uploads/NYC_OpenData_TechnicalStandardsManual.pdf), section 2.3.2, describes published Open Data as a public resource available without restriction or licensing requirements. The dataset metadata does not supply a separate SPDX license; no Creative Commons license is asserted here. Source ownership and accuracy remain with the publishing agency.

`data/provenance.json` retains the full filtered query, source row count, retrieval date, cutoff and SHA-256 checksum. The cohort is 1 November 2025 inclusive to 8 November 2025 exclusive; closure is analysed through 1 December 2025 exclusive. No claim is made that historical records are immutable or that closure confirms resolution.

The source provides a changed Problem label under the existing API name `complaint_type`; the code retains that API field name. These charts are independent transformations, not an official city performance report. No external portfolio code was copied.
