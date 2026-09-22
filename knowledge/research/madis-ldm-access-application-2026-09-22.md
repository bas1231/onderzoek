# MADIS LDM access application — 2026-09-22

## Status

- Application submitted successfully to NOAA MADIS on 2026-09-22.
- Request type: **Real-time**.
- Distribution method: **LDM**.
- NOAA confirmation states that applications received by COB Thursday are processed the following Monday.
- Expected next step: wait for MADIS Support approval/account-creation email, then configure and validate LDM ingest on the Strix.

## Confirmed requested datasets

The submitted form was prepared around the following high-priority surface-observation datasets:

- **METAR (standard)**
- **Integrated Mesonet**
- **1-minute ASOS**

`Maritime` was also evaluated as useful for coastal upstream observations, but its final checkbox state at submission was not independently captured in the repository record.

## Technical purpose supplied in the application

> Personal non-commercial real-time weather monitoring and research project. I am developing a system that continuously ingests surface weather observations to study short-term weather changes, station behavior, spatial differences between nearby observing sites, and data-delivery latency across multiple public meteorological sources. Continuous low-latency access is required for this research.

The LDM request is specifically motivated by continuous low-latency ingestion rather than on-demand retrieval.

## Research relevance

MADIS access is intended to support observation-latency and spatial-lead research, including:

1. **1-minute ASOS / METAR latency** — compare observation time, ingest/arrival time, downstream publication time, and market-data reaction time.
2. **Integrated Mesonet spatial lead** — identify nearby/upstream stations around target weather stations and test whether precipitation, wind, temperature, pavement/RWIS, or other surface observations provide useful lead time.
3. **Cross-source timing** — compare MADIS observations with other public weather sources while preserving point-in-time timestamps and provenance.

No trading or execution action is authorized by this record. Any downstream use must remain subject to the project risk gates and the applicable MADIS data-use/restriction terms.

## Privacy / security note

The GitHub repository is public. Therefore the following application details are deliberately **not stored here**:

- applicant home address
- phone number
- email address
- public IP address
- other account credentials or access secrets

The LDM host is the user's local Strix Linux workstation. Exact network identifiers should remain local and must not be committed to the public repository.

## Next gate after approval

After MADIS approval:

1. Preserve the approval email/instructions locally.
2. Configure LDM on the Strix according to NOAA-provided access details.
3. Verify receipt of the requested feeds.
4. Record product identifiers, station coverage, source timestamps, local receipt timestamps, and clock-health evidence.
5. Run a prospective latency comparison before drawing any economic conclusion.
6. Keep status **NO_PROVEN_EDGE** until prospective evidence supports otherwise.
