# Revision handling

Phase 10 accepts a Phase 9 `DEFERRED_REVISION` artifact only when its supported
official release metadata gives an unambiguous order. The repository contains
one verified real release, so all multi-release behavior is verified with
synthetic fixtures rather than fabricated Stats NZ artifacts.

## Identities and precedence

- Release identity: `dataset_year + dataset_version + source_sha256`.
- Artifact identity: exact source-file SHA-256, also used as `ingestion_id`.
- Observation identity: `Year + Industry_aggregation_NZSIOC +
  Industry_code_NZSIOC + Variable_code`.
- Revision identity: deterministic SHA-256 of the revision contract, previous
  artifact hashes, and incoming artifact hash.

For each overlapping observation, the incoming `dataset_year` must be strictly
greater than the selected current release's `dataset_year`. `dataset_year` is
part of the approved ingestion metadata and corresponds to the named AES
release. Filename, checksum, ingestion time, and free-form `dataset_version`
text never determine precedence.

Two artifacts with the same greatest `dataset_year` for one observation are
ambiguous. They remain deferred even if one version string says `final`; the
project has no approved ordering contract for such strings.

## Historical and current grains

Bronze history grain:

```text
ingestion_id (source artifact SHA-256)
+ source_row_number
```

Multiple official releases may therefore retain separate raw rows for the same
observation without losing either artifact. Bronze is an append-only release
history at this project scale.

Silver current-view grain:

```text
Year
+ Industry_aggregation_NZSIOC
+ Industry_code_NZSIOC
+ Variable_code
```

Silver selects the greatest unambiguous `dataset_year` independently for every
observation. An observation absent from the incoming release remains selected
from its prior release; absence is reported and is not interpreted as deletion.
Existing Silver parsing and validation then run unchanged over that current
Bronze view.

The selected Silver row retains the current release lineage. Previous release
lineage remains auditable through Bronze history and the persisted revision
report, rather than duplicating history into the analytical current view.

## Classification and audit

The report distinguishes unchanged republications, raw `Value` revisions,
published metadata revisions, new observations, and observations absent from
the incoming release. Value transitions include published, confidential, and
suppressed states. Metadata comparison covers industry name, units, variable
name/category, and the ANZSIC06 mapping.

Reports are stored once per incoming SHA-256 under `data/revisions/`. They
contain previous and incoming release identities, classification counts,
transition counts, precedence outcome, current-view changes, and downstream
rebuild decisions. Repeating an applied or deferred artifact returns the same
report without duplicating Bronze or rebuilding Silver/Gold.

## Operation

Configure the existing source and layer paths plus `REVISION_REPORT_DIR`, then
run:

```powershell
python -m nz_industry_benchmarking.revision
```

An eligible revision is appended to Bronze, Silver is rebuilt as a unique
current view, and Gold is rebuilt from Silver with the approved M1-M7 rules
unchanged. Ambiguous precedence writes a `DEFERRED_AMBIGUOUS` report and does not
modify Bronze, Silver, or Gold.
