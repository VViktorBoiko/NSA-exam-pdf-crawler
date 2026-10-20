NSA Exam PDF Crawler and Dataset Builder

1\. Project Overview

This project collects and organizes examination task PDFs and assessment instructions published on the Lithuanian National Agency for Education (Nacionalinė švietimo agentūra, NSA) website.

The crawler extracts PDF links and available metadata, classifies documents, and prepares a structured dataset connecting examination tasks with potentially corresponding assessment instructions.

The project focuses on two examination categories:

VBE — State Maturity Examinations (Valstybiniai brandos egzaminai).

PUPP — Basic Education Achievement Tests (Pagrindinio ugdymo pasiekimų patikrinimai).

The workflow consists of several independent scripts that are executed in sequence. It is not a single-command pipeline.

2\. Data Sources

The crawler uses the following official NSA pages:

VBE examination tasks

(https://www.nsa.smsm.lt/pasiekimu-departamentas/egzaminai-ir-pasiekimu-patikrinimai/valstybiniai-brandos-egzaminai/egzaminu-uzduotys/)

VBE assessment instructions

(https://www.nsa.smsm.lt/pasiekimu-departamentas/egzaminai-ir-pasiekimu-patikrinimai/valstybiniai-brandos-egzaminai/vertinimo-instrukcijos/)

PUPP examination tasks

(https://www.nsa.smsm.lt/pasiekimu-departamentas/egzaminai-ir-pasiekimu-patikrinimai/pagrindinio-ugdymo-pasiekimu-patikrinimai/pupp-uzduotys/)

PUPP assessment instructions

(https://www.nsa.smsm.lt/pasiekimu-departamentas/egzaminai-ir-pasiekimu-patikrinimai/pagrindinio-ugdymo-pasiekimu-patikrinimai/pupp-vertinimo-instrukcijos/)



The project excludes `beta.etestavimas.lt` and does not use it as a data source.

A distinction is made between assessment instructions (vertinimo instrukcijos) and blank answer sheets (atsakymų lapas). Blank answer sheets are not treated as assessment instructions.

3\. Features

\- Collects PDF links from the official NSA pages.

\- Processes PDF links found in HTML tables and supports collection of links outside tables where implemented.

\- Extracts available metadata, including year, subject, examination type, session, part, and VBE level.

\- Classifies documents into categories such as tasks, assessment instructions, sample tasks, and other related materials.

\- Downloads PDFs and validates downloaded files.

\- Records download status, file paths, and checksums in a download manifest.

\- Matches tasks with potential assessment instructions using metadata.

\- Produces a task-oriented JSON dataset containing matching results and review information.

\- Includes scripts for archive auditing, diagnostics, and selected repair operations.

4\. Project Structure

The main scripts are:

main\_classification\_v5.py

Main crawler: collects PDF links and classifies documents while extracting available metadata.

download\_pdfs.py

Downloads PDFs, validates files, and maintains a download manifest.

match\_documents\_v5.py

Finds potential task–assessment-instruction matches using metadata.

build\_final\_dataset.py

Combines the document catalog, matching results, and download manifest into the final dataset.

audit\_pdf\_archive.py

Checks the local PDF archive, file integrity, checksums, and metadata consistency.

crawler.py

Early experimental crawler prototype.

main.py, main\_improved.py, and earlier classification or matching scripts

Earlier development and experimental versions.

Additional scripts are provided for metadata corrections, diagnostics, match analysis, and selected file-repair tasks.

Generated data is stored in the `output/` directory. Downloaded PDFs are organized under `output/pdfs/`, grouped by document type and year.

5\. Requirements

\- Python 3

\- Internet access to the official NSA website

\- The Python packages listed below

Install the dependencies:

python -m pip install requests beautifulsoup4 urllib3

Run commands from the project root directory.

6\. How to Run

The workflow is executed step by step. Each stage produces files required by later stages.

Step 1: Crawl and classify documents

python main\_classification\_v5.py

The script processes the four configured NSA source pages and creates:

output/documents\_preview.json

This JSON file contains the collected document records, including source URLs, filenames, classifications, and available metadata.

The script also writes crawler logs to `crawler.log`.

Step 2: Download PDF files

python download\_pdfs.py

The downloader reads `output/documents\_preview.json`, downloads the unique PDF URLs, validates the downloaded files, and records their status.

The main outputs are:

output/pdfs/

output/download\_manifest.json

output/download\_summary.json

output/download\_errors.log

The downloader can also be run with a limit during testing:

python download\_pdfs.py --limit 3

To retry URLs previously recorded as errors:

python download\_pdfs.py --retry-errors

Step 3: Match tasks with assessment instructions

python match\_documents\_v5.py --input output/documents\_preview.json --out output

The matching script compares available metadata, including year, subject, examination type, session, part, and level where applicable.

It generates:

output/matches\_v5.json

output/match\_analysis\_v5.json

Matching is metadata-based. The script identifies potential matches and flags ambiguous or conflicting cases rather than treating every candidate as confirmed.

Step 4: Build the final dataset

python build\_final\_dataset.py

This step combines the document catalog, matching results, and download manifest.

It generates:

output/final\_dataset.json

output/final\_summary.json

The final dataset contains one record per examination task and includes the task's download information, any selected assessment instruction, matching status, candidate information, and review notes.

Step 5: Audit the downloaded archive

python audit\_pdf\_archive.py

The audit script checks the PDF archive against the document catalog and download manifest. It verifies file presence, file size, PDF signatures, checksums, and consistency between metadata and directory structure.

The report is saved as:

output/archive\_audit.json

The audit should be run after the downloads and dataset outputs have been generated.

7\. Metadata

The crawler attempts to extract the following fields when the source page or filename provides sufficient information:

`year` Examination year

`subject` Examination subject

`exam\_type` Examination category or type as identified by the crawler

`session` Main (\*pagrindinė\*) or resit (\*pakartotinė\*) session

`srautas` Stream, when identifiable

`dalis` Examination part, such as I or II

`level` VBE level, such as \*bendrasis\* or \*išplėstinis\*

Metadata is not always explicitly available. Unidentified values may remain `null` rather than being inferred without sufficient evidence.

8\. Matching and Status Interpretation

The matching stage is intended to identify likely relationships between examination tasks and assessment instructions.

The matching results are preliminary and may require manual review. Filenames and source-page metadata are not always consistent, and multiple plausible instruction files may exist for the same examination.

In `final\_dataset.json`, the main status values are:

`found` — a provisional metadata-based match was selected and both the task PDF and selected instruction PDF are available locally. This does not mean that their contents have been compared.

`missing` — no instruction candidate was selected. This may mean that no compatible candidate was found or that potential candidates require review.

`broken\_link` — the task PDF or a provisionally selected instruction PDF is unavailable locally.

The dataset also retains matching details and candidate information to support subsequent manual verification.

9\. Error Handling and Validation

The crawler logs page-fetching errors and continues processing other source pages when a page cannot be retrieved.

The downloader records failed downloads in its manifest and error log. It supports retries for transient HTTP errors and validates downloaded PDFs before accepting them.

The archive audit provides an additional verification stage by checking file integrity and consistency between the downloaded files, manifest, and document catalog.

10.Limitations

Some source records do not provide enough information to extract every metadata field.

NSA filenames and document labels are not fully standardized.

Automatic task–instruction matching is preliminary and requires manual verification where indicated.

A successful download or a found status does not prove that the task and assessment instruction contents have been compared.

The final dataset distinguishes confirmed file availability from unresolved matching cases.

